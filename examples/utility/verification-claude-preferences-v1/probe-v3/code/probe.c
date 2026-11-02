
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>
static int hex32(const char *v) {
 return strlen(v)==32 && strspn(v,"0123456789abcdef")==32;
}
int main(int argc,char **argv) {
 const char *prefix="org.autoengineering.qualification.";
 if(argc!=4 || strncmp(argv[2],prefix,strlen(prefix)) ||
    !hex32(argv[2]+strlen(prefix)) || !hex32(argv[3])) return 2;
 int seed=!strcmp(argv[1],"seed"), clear=!strcmp(argv[1],"clear");
 if(!seed && !clear && strcmp(argv[1],"read")) return 2;
 CFStringRef domain=CFStringCreateWithCString(NULL,argv[2],kCFStringEncodingUTF8);
 CFStringRef expected=CFStringCreateWithCString(NULL,argv[3],kCFStringEncodingUTF8);
 CFStringRef key=CFSTR("AEQualificationCanary");
 if(!domain || !expected) return 3;
 CFPropertyListRef before=CFPreferencesCopyValue(key,domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
 if((seed && before) || (clear && before && !CFEqual(before,expected))) return 4;
 if(before) CFRelease(before);
 int synchronized=-1;
 if(seed || clear) {
  CFPreferencesSetValue(key,seed?expected:NULL,domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
  synchronized=CFPreferencesSynchronize(domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost)?1:0;
 }
 CFPropertyListRef value=CFPreferencesCopyValue(key,domain,kCFPreferencesCurrentUser,kCFPreferencesAnyHost);
 printf("{\"present\":%d,\"visible\":%d,\"synchronized\":%d}\n",
        value?1:0,value&&CFEqual(value,expected)?1:0,synchronized);
 if(value) CFRelease(value);
 CFRelease(expected);CFRelease(domain);return 0;
}
