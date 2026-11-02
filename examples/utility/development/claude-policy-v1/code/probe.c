
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
static int read_ok(const char *p) { int f=open(p,O_RDONLY); if(f<0)return 0;close(f);return 1; }
static int read_denied(const char *p) { int f=open(p,O_RDONLY);int e=errno;if(f>=0)close(f);return f<0&&(e==EPERM||e==EACCES); }
static int write_ok(const char *p) {int f=open(p,O_WRONLY|O_CREAT,0600);if(f<0)return 0;close(f);return 1;}
static int write_denied(const char *p) {int f=open(p,O_WRONLY|O_CREAT,0600);int e=errno;if(f>=0)close(f);return f<0&&(e==EPERM||e==EACCES);}
static int connect_result(int family,int port,const char *path) {
 int f=socket(family,SOCK_STREAM,0);if(f<0)return -1;fcntl(f,F_SETFL,O_NONBLOCK);int r;
 if(family==AF_INET){struct sockaddr_in a={0};a.sin_family=family;a.sin_port=htons(port);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);r=connect(f,(struct sockaddr*)&a,sizeof(a));}
 else {struct sockaddr_un a={0};a.sun_family=family;if(strlen(path)>=sizeof(a.sun_path)){close(f);return -1;}strcpy(a.sun_path,path);r=connect(f,(struct sockaddr*)&a,sizeof(a));}
 int e=errno;if(r<0&&e==EINPROGRESS){struct pollfd p={f,POLLOUT,0};if(poll(&p,1,1000)!=1){close(f);return -1;}socklen_t z=sizeof(e);if(getsockopt(f,SOL_SOCKET,SO_ERROR,&e,&z)){close(f);return -1;}r=e==0?0:-1;}
 close(f);return r==0?1:(e==EPERM||e==EACCES?0:-1);
}
static int exec_denied(void){pid_t p=fork();if(p<0)return -1;if(!p){execl("/usr/bin/true","true",NULL);_exit(errno==EPERM||errno==EACCES?77:78);}int s;if(waitpid(p,&s,0)<0)return -1;return WIFEXITED(s)&&WEXITSTATUS(s)==77;}
int main(int n,char **a){if(n!=14)return 2;
 int linked=link(a[2],a[9]);int saved=errno;
 int hardlink_denied=linked<0&&(saved==EPERM||saved==EACCES);
 if(linked==0)hardlink_denied=read_denied(a[9]);
 printf("{\"allowed_read\":%d,\"private_read_denied\":%d,\"credential_read\":%d,\"outside_write_denied\":%d,\"home_write\":%d,\"workspace_write_denied\":%d,\"symlink_read_denied\":%d,\"symlink_write_denied\":%d,\"hardlink_read_denied\":%d,\"endpoint_allowed\":%d,\"other_tcp_denied\":%d,\"unix_denied\":%d,\"exec_denied\":%d,\"checkout_read_denied\":%d}\n",
 read_ok(a[1]),read_denied(a[2]),read_ok(a[3]),write_denied(a[4]),write_ok(a[5]),write_denied(a[6]),read_denied(a[7]),write_denied(a[8]),hardlink_denied,connect_result(AF_INET,atoi(a[10]),"")==1,connect_result(AF_INET,atoi(a[11]),"")==0,connect_result(AF_UNIX,0,a[12])==0,exec_denied(),read_denied(a[13]));return 0;}
