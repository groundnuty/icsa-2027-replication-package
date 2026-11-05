/* portmap.so: the network shim of a sandbox on a site_a node, where a user has no network namespace (max_net_namespaces=0) and cannot bind a port below 1024 (ip_unprivileged_port_start=1024).
 *
 * It is loaded into EVERY dynamically linked process of the container through /etc/ld.so.preload (bound read-only), NOT through LD_PRELOAD, and it reads its settings from a file bound
 * read-only at /opt/hpcsbx/portmap.conf, NOT from the environment: a cell that clears its environment, or starts children with env={}, keeps it. What it cannot stop: a static binary and a raw
 * connect(2) made with syscall(2) (no seccomp filter can read a sockaddr). That is a deliberate act, and the sandbox's record says so.
 *
 * portmap.conf, one setting per line:
 *   mode gate|agent
 *   offset N            ports below 1024 are moved up by N (443 -> 20443)
 *   bind A.B.C.D        (gate) bind() of an IPv4 socket to INADDR_ANY or to 127/8 is made to this address; a port below 1024 becomes port+offset
 *   gate A.B.C.D[,...]  (agent) the sandbox's own gate address(es): connect() to one of them on a port below 1024 goes to port+offset
 *   deny_port N         (agent) connect() to loopback on this port is refused (the provider's own port, in case it listens on this node's loopback)
 *
 * In mode agent connect(), sendto() and sendmsg() on an AF_INET/AF_INET6 socket are allowed only to the gate address(es) and to loopback (except deny_port); every other destination fails
 * with ENETUNREACH, as it would with no network. AF_UNIX is not touched. In mode gate only bind() is changed.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>

#define CONF "/opt/hpcsbx/portmap.conf"
#define MAXG 8
#define MAXD 16

static int agent, offset, failed_closed;
static struct in_addr bindaddr, gates[MAXG];
static int have_bind, ngates, denied[MAXD], ndenied;

static pthread_once_t once = PTHREAD_ONCE_INIT;

static void load_once(void) {
    int saved = errno;
    FILE *f = fopen(CONF, "re");
    if (!f) {
        /* absent: a process outside a sandbox (the file is bound read-only into the container, a cell cannot remove it). Any other failure (EMFILE, ENFILE, ENOMEM)
         * must not open the network: the process is refused every connect instead. The constructor below reads the file before the program's first line runs, so a cell cannot get here by
         * exhausting its descriptors first; this is the fallback for a process started by something that closed all descriptors. */
        if (errno != ENOENT)
            agent = failed_closed = 1;
        errno = saved;
        return;
    }
    char line[512];
    while (fgets(line, sizeof line, f)) {
        char key[64], val[400];
        if (sscanf(line, "%63s %399[^\n]", key, val) < 2)
            continue;
        if (!strcmp(key, "mode"))
            agent = !strcmp(val, "agent");
        else if (!strcmp(key, "offset"))
            offset = atoi(val);
        else if (!strcmp(key, "bind"))
            have_bind = inet_pton(AF_INET, val, &bindaddr) == 1;
        else if (!strcmp(key, "gate")) {
            char *save = NULL;
            for (char *t = strtok_r(val, ",", &save); t && ngates < MAXG; t = strtok_r(NULL, ",", &save))
                if (inet_pton(AF_INET, t, &gates[ngates]) == 1)
                    ngates++;
        } else if (!strcmp(key, "deny_port") && ndenied < MAXD)
            denied[ndenied++] = atoi(val);
    }
    fclose(f);
    errno = saved;
}

static void load(void) {
    pthread_once(&once, load_once);        /* every thread waits for the one that reads the file: no thread sees a half-read configuration */
}

__attribute__((constructor)) static void init(void) {
    load();
}

static int is_gate(uint32_t addr_net) {
    for (int i = 0; i < ngates; i++)
        if (gates[i].s_addr == addr_net)
            return 1;
    return 0;
}

static int port_denied(unsigned port) {
    for (int i = 0; i < ndenied; i++)
        if ((unsigned)denied[i] == port)
            return 1;
    return 0;
}

/* 0: allowed (*out holds the destination to use when *rewritten), -1: refused (errno set) */
static int check_dest(const struct sockaddr *addr, socklen_t len, struct sockaddr_in *out, int *rewritten) {
    *rewritten = 0;
    if (!agent || !addr)
        return 0;
    if (failed_closed && addr->sa_family != AF_UNIX) {
        errno = ENETUNREACH;
        return -1;
    }
    if (addr->sa_family == AF_INET && len >= sizeof(struct sockaddr_in)) {
        memcpy(out, addr, sizeof *out);
        unsigned port = ntohs(out->sin_port);
        uint32_t host = ntohl(out->sin_addr.s_addr);
        if (is_gate(out->sin_addr.s_addr)) {
            if (port > 0 && port < 1024) {
                out->sin_port = htons(port + offset);
                *rewritten = 1;
            }
            return 0;
        }
        if ((host >> 24) == 127 || host == 0) {
            if (port_denied(port)) {
                errno = ENETUNREACH;
                return -1;
            }
            return 0;
        }
        errno = ENETUNREACH;
        return -1;
    }
    if (addr->sa_family == AF_INET6 && len >= sizeof(struct sockaddr_in6)) {
        const struct sockaddr_in6 *s6 = (const struct sockaddr_in6 *)addr;
        if (IN6_IS_ADDR_LOOPBACK(&s6->sin6_addr) || IN6_IS_ADDR_UNSPECIFIED(&s6->sin6_addr)) {
            if (port_denied(ntohs(s6->sin6_port))) {
                errno = ENETUNREACH;
                return -1;
            }
            return 0;
        }
        errno = ENETUNREACH;
        return -1;
    }
    return 0;                             /* AF_UNIX and the rest */
}

int bind(int fd, const struct sockaddr *addr, socklen_t len) {
    static int (*real)(int, const struct sockaddr *, socklen_t);
    if (!real)
        real = (int (*)(int, const struct sockaddr *, socklen_t))dlsym(RTLD_NEXT, "bind");
    load();
    if (!agent && have_bind && addr && addr->sa_family == AF_INET && len >= sizeof(struct sockaddr_in)) {
        struct sockaddr_in sin;
        memcpy(&sin, addr, sizeof sin);
        uint32_t host = ntohl(sin.sin_addr.s_addr);
        if (host == INADDR_ANY || (host >> 24) == 127) {
            unsigned port = ntohs(sin.sin_port);
            sin.sin_addr = bindaddr;
            if (port > 0 && port < 1024)
                sin.sin_port = htons(port + offset);
            return real(fd, (struct sockaddr *)&sin, sizeof sin);
        }
    }
    return real(fd, addr, len);
}

int connect(int fd, const struct sockaddr *addr, socklen_t len) {
    static int (*real)(int, const struct sockaddr *, socklen_t);
    if (!real)
        real = (int (*)(int, const struct sockaddr *, socklen_t))dlsym(RTLD_NEXT, "connect");
    load();
    struct sockaddr_in sin;
    int rw;
    if (check_dest(addr, len, &sin, &rw) < 0)
        return -1;
    if (rw)
        return real(fd, (struct sockaddr *)&sin, sizeof sin);
    return real(fd, addr, len);
}

ssize_t sendto(int fd, const void *buf, size_t n, int flags, const struct sockaddr *addr, socklen_t len) {
    static ssize_t (*real)(int, const void *, size_t, int, const struct sockaddr *, socklen_t);
    if (!real)
        real = (ssize_t (*)(int, const void *, size_t, int, const struct sockaddr *, socklen_t))dlsym(RTLD_NEXT, "sendto");
    load();
    struct sockaddr_in sin;
    int rw;
    if (addr && check_dest(addr, len, &sin, &rw) < 0)
        return -1;
    if (addr && rw)
        return real(fd, buf, n, flags, (struct sockaddr *)&sin, sizeof sin);
    return real(fd, buf, n, flags, addr, len);
}

ssize_t sendmsg(int fd, const struct msghdr *msg, int flags) {
    static ssize_t (*real)(int, const struct msghdr *, int);
    if (!real)
        real = (ssize_t (*)(int, const struct msghdr *, int))dlsym(RTLD_NEXT, "sendmsg");
    load();
    struct sockaddr_in sin;
    int rw;
    if (msg && msg->msg_name && check_dest((const struct sockaddr *)msg->msg_name, msg->msg_namelen, &sin, &rw) < 0)
        return -1;
    return real(fd, msg, flags);        /* a UDP destination is never rewritten: the gate speaks TCP */
}

int sendmmsg(int fd, struct mmsghdr *vec, unsigned int vlen, int flags) {
    static int (*real)(int, struct mmsghdr *, unsigned int, int);
    if (!real)
        real = (int (*)(int, struct mmsghdr *, unsigned int, int))dlsym(RTLD_NEXT, "sendmmsg");
    load();
    struct sockaddr_in sin;
    int rw;
    for (unsigned int i = 0; i < vlen; i++)
        if (vec[i].msg_hdr.msg_name && check_dest((const struct sockaddr *)vec[i].msg_hdr.msg_name, vec[i].msg_hdr.msg_namelen, &sin, &rw) < 0)
            return -1;                  /* one refused destination refuses the whole call */
    return real(fd, vec, vlen, flags);
}
