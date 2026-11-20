/* Native Finder entrypoint; the existing Terminal owns server output and Ctrl+C. */
#include <CoreFoundation/CoreFoundation.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int fail(void) {
    perror("Bowl Bound launcher");
    CFUserNotificationDisplayAlert(
        0, kCFUserNotificationStopAlertLevel, NULL, NULL, NULL,
        CFSTR("Bowl Bound could not start"),
        CFSTR("The Terminal launcher could not be opened. Reinstall the complete app "
              "and consult the installation guide."),
        CFSTR("OK"), NULL, NULL, NULL);
    return 1;
}

int main(void) {
    char raw[PATH_MAX], resolved[PATH_MAX], command[PATH_MAX];
    uint32_t size = sizeof(raw);
    if (_NSGetExecutablePath(raw, &size) != 0 || realpath(raw, resolved) == NULL)
        return fail();
    char *separator = strrchr(resolved, '/');
    if (separator == NULL)
        return fail();
    *separator = '\0';
    int length = snprintf(command, sizeof(command), "%s/../Resources/start.command", resolved);
    if (length < 0 || (size_t)length >= sizeof(command))
        return fail();
    execl("/usr/bin/open", "open", "-a", "Terminal", command, (char *)NULL);
    return fail();
}
