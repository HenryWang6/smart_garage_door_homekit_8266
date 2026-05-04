"""
Patch the Arduino-HomeKit-ESP8266 library to fix HomeKit pairing bugs.

Runs as a PlatformIO pre: extra_script — patches the library source files
after PlatformIO downloads them but before compilation.
"""

import os
from os.path import join, exists

Import("env")

# Original (buggy) code in arduino_homekit_server.cpp write() function
WRITE_OLD = """\tint write_size = context->socket->write(data, data_size);
\tCLIENT_VERBOSE(context, "Sending data of size %d", data_size);
\tif (write_size != data_size) {
\t\tcontext->error_write = true;
\t\t//context->socket->keepAlive(1, 1, 1);\t// fast disconnected internally in 1 second.
\t\tcontext->socket->stop();
\t\tCLIENT_ERROR(context, "socket.write, data_size=%d, write_size=%d", data_size, write_size);
\t}"""

# Fixed code with retry loop for short writes
WRITE_NEW = """\tint total_written = 0;
\tint retries = 0;
\twhile (total_written < data_size) {
\t\tsystem_soft_wdt_feed();
\t\tesp_yield();
\t\tint write_size = context->socket->write(data + total_written, data_size - total_written);
\t\tif (write_size > 0) {
\t\t\ttotal_written += write_size;
\t\t\tretries = 0;
\t\t\tcontinue;
\t\t}
\t\tretries++;
\t\tif (retries > 10 || !context->socket->connected()) {
\t\t\tcontext->error_write = true;
\t\t\tcontext->socket->stop();
\t\t\tCLIENT_ERROR(context, "socket.write failed, data_size=%d, written=%d", data_size, total_written);
\t\t\treturn;
\t\t}
\t\tdelay(50);
\t}"""

# Original (buggy) code in storage.c homekit_storage_reset_pairing_data()
# Returns after clearing only the first active pairing
STORAGE_OLD = """            memset(&data, 0, 4);
            if (!spiflash_write(PAIRINGS_ADDR + (sizeof(data) * i) + 76, (uint32_t *) &data, 4)) {
                ERROR("Failed to remove pairing from HomeKit storage");
                return -2;
            }

            return 0;"""

# Fixed code — loop continues to clear all 16 pairing slots
STORAGE_NEW = """            memset(&data, 0, 4);
            if (!spiflash_write(PAIRINGS_ADDR + (sizeof(data) * i) + 76, (uint32_t *) &data, 4)) {
                ERROR("Failed to remove pairing from HomeKit storage");
                return -2;
            }"""


def patch_file(filepath, old_text, new_text, description):
    with open(filepath, "r") as f:
        content = f.read()

    if old_text in content:
        content = content.replace(old_text, new_text, 1)
        with open(filepath, "w") as f:
            f.write(content)
        print("patch_homekit: %s — PATCHED" % description)
        return True

    if new_text in content:
        print("patch_homekit: %s — already patched" % description)
        return True

    print("patch_homekit: %s — WARNING: target not found, skipping" % description)
    return False


def main():
    project_dir = env.subst("$PROJECT_DIR")
    libdeps_base = join(project_dir, ".pio", "libdeps")

    if not exists(libdeps_base):
        print("patch_homekit: libdeps not found, skipping")
        return

    # Find all copies of the HomeKit library across all envs
    copies = []
    for root, dirs, files in os.walk(libdeps_base):
        if "arduino_homekit_server.cpp" in files and exists(join(root, "storage.c")):
            copies.append(root)

    if not copies:
        print("patch_homekit: HomeKit library not found, skipping")
        return

    total_applied = 0
    for lib_dir in copies:
        server_file = join(lib_dir, "arduino_homekit_server.cpp")
        storage_file = join(lib_dir, "storage.c")
        env_name = os.path.basename(os.path.dirname(lib_dir))
        print("patch_homekit: Patching %s in %s" % (os.path.basename(lib_dir), env_name))

        patch_file(server_file, WRITE_OLD, WRITE_NEW, "socket write retry")
        patch_file(storage_file, STORAGE_OLD, STORAGE_NEW, "pairing reset all-slots")

    print("patch_homekit: done")


main()
