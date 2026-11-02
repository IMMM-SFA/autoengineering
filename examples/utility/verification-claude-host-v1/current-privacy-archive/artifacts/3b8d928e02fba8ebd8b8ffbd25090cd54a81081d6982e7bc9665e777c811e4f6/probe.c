
#include <arpa/inet.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/mman.h>
#include <sys/sysctl.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>

static int denied(int rc) {
    int saved = errno;
    if (rc >= 0) close(rc);
    return rc < 0 && (saved == EACCES || saved == EPERM);
}
static int opened(const char *path, int flags) {
    int fd = open(path, flags, 0600);
    if (fd < 0) return 0;
    close(fd);
    return 1;
}
static int allowed_read(const char *path) {
    const char *expected = "approved native probe brief\n";
    char value[128] = {0};
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    ssize_t count = read(fd, value, sizeof(value));
    close(fd);
    return count == (ssize_t)strlen(expected) && !memcmp(value, expected, count);
}
/* Return 1 for connected, 0 for denied, and -1 for an invalid control. */
static int connected(int family, int port, const char *path) {
    int fd = socket(family, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    fcntl(fd, F_SETFL, O_NONBLOCK);
    int rc;
    if (family == AF_INET) {
        struct sockaddr_in address = {0};
        address.sin_family = AF_INET;
        address.sin_port = htons(port);
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        rc = connect(fd, (struct sockaddr *)&address, sizeof(address));
    } else {
        struct sockaddr_un address = {0};
        address.sun_family = AF_UNIX;
        if (strlen(path) >= sizeof(address.sun_path)) { close(fd); return -1; }
        strcpy(address.sun_path, path);
        rc = connect(fd, (struct sockaddr *)&address, sizeof(address));
    }
    int saved = errno;
    if (rc < 0 && saved == EINPROGRESS) {
        struct pollfd wait = {fd, POLLOUT, 0};
        if (poll(&wait, 1, 1000) != 1) { close(fd); return -1; }
        socklen_t size = sizeof(saved);
        if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &saved, &size)) {
            close(fd); return -1;
        }
        rc = saved == 0 ? 0 : -1;
    }
    close(fd);
    return rc == 0 ? 1 : (saved == EACCES || saved == EPERM ? 0 : -1);
}
static int denied_exec(void) {
    pid_t child = fork();
    if (child < 0) return 0;
    if (!child) {
        char *const args[] = {"/usr/bin/true", NULL};
        execv(args[0], args);
        _exit(errno == EACCES || errno == EPERM ? 123 : 124);
    }
    int status;
    if (waitpid(child, &status, 0) != child) return 0;
    return WIFEXITED(status) && WEXITSTATUS(status) == 123;
}
/* Public CoreFoundation APIs, loaded dynamically so no extra link dependency
   enters the POSIX probes. Domains name only the two synthetic plist paths. */
static int preference_read(const char *domain_name) {
    void *library = dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation", RTLD_NOW);
    if (!library) return -1;
    void *(*string)(void *, const char *, unsigned int) = dlsym(library, "CFStringCreateWithCString");
    void *(*copy)(void *, void *, void *, void *) = dlsym(library, "CFPreferencesCopyValue");
    unsigned char (*equal)(void *, void *) = dlsym(library, "CFEqual");
    void (*release)(void *) = dlsym(library, "CFRelease");
    void **current = dlsym(library, "kCFPreferencesCurrentUser");
    void **any = dlsym(library, "kCFPreferencesAnyHost");
    if (!string || !copy || !equal || !release || !current || !any) return -1;
    void *key = string(NULL, "Canary", 0x08000100);
    void *domain = string(NULL, domain_name, 0x08000100);
    void *expected = string(NULL, "synthetic preference canary", 0x08000100);
    if (!key || !domain || !expected) return -1;
    void *value = copy(key, domain, *current, *any);
    int result = value ? (equal(value, expected) ? 1 : -1) : 0;
    if (value) release(value);
    release(expected); release(domain); release(key);
    dlclose(library);
    return result;
}
static int shared_memory_denied(const char *name) {
    int fd = shm_open(name, O_RDONLY, 0);
    if (fd < 0) {
        if (errno == EACCES || errno == EPERM) {
            fprintf(stderr, "synthetic shm open denied: %d\n", errno);
            return 1;
        }
        _exit(4);  /* A missing or broken fixture cannot establish denial. */
    }
    size_t size = strlen("synthetic shared-memory canary");
    char *bytes = mmap(NULL, size, PROT_READ, MAP_SHARED, fd, 0);
    int saved = errno;
    close(fd);
    if (bytes == MAP_FAILED) {
        if (saved == EACCES || saved == EPERM) {
            fprintf(stderr, "synthetic shm map denied: %d\n", saved);
            return 1;
        }
        _exit(4);
    }
    int matched = !memcmp(bytes, "synthetic shared-memory canary", size);
    munmap(bytes, size);
    if (!matched) _exit(3);
    return 0;
}
static int environment_denied(const char *pid) {
    int name[] = {CTL_KERN, KERN_PROCARGS2, atoi(pid)};
    size_t size = 0;
    if (sysctl(name, 3, NULL, &size, NULL, 0)) {
        if (errno == EACCES || errno == EPERM) return 1;
        _exit(5);
    }
    if (!size || size > 1048576) _exit(5);
    char *bytes = calloc(size, 1);
    if (!bytes) _exit(5);
    if (sysctl(name, 3, bytes, &size, NULL, 0)) {
        int saved = errno;
        free(bytes);
        if (saved == EACCES || saved == EPERM) return 1;
        _exit(5);
    }
    const char *expected = "AE_NATIVE_QUAL_ENV=synthetic-environment-canary";
    int found = 0;
    for (size_t i = 0; i + strlen(expected) <= size; i++) {
        if (!memcmp(bytes + i, expected, strlen(expected))) { found = 1; break; }
    }
    free(bytes);
    if (!found) _exit(5);
    return 0;
}
int main(int argc, char **argv) {
    if (argc != 19) return 2;
    int values[19];
    for (int i = 0; i < 5; i++) values[i] = denied(open(argv[i+1], O_RDONLY));
    values[5] = denied(open(argv[6], O_WRONLY | O_CREAT, 0600));
    values[6] = allowed_read(argv[7]);
    values[7] = denied(open(argv[8], O_WRONLY | O_CREAT, 0600));
    values[8] = opened(argv[9], O_WRONLY | O_CREAT);
    values[9] = denied(open(argv[10], O_RDONLY));
    values[10] = denied(open(argv[11], O_WRONLY));
    values[11] = connected(AF_INET, atoi(argv[12]), NULL) == 1;
    values[12] = connected(AF_INET, atoi(argv[13]), NULL) == 0;
    values[13] = connected(AF_UNIX, 0, argv[14]) == 0;
    values[14] = denied_exec();
    values[15] = preference_read(argv[15]) == 0;
    values[16] = preference_read(argv[16]) == 0;
    values[17] = shared_memory_denied(argv[17]);
    values[18] = environment_denied(argv[18]);
    printf("[");
    for (int i = 0; i < 19; i++) printf("%s%s", i ? "," : "", values[i] ? "true" : "false");
    printf("]\n");
    return 0;
}
