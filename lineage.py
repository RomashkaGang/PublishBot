import hashlib
import os
from glob import glob
from os.path import join
from time import time
from datetime import datetime

from git import Repo
from telegram.utils.helpers import escape_markdown
from telethon.sync import TelegramClient
from telethon.tl.custom import Message

os.environ['TZ'] = 'Europe/Moscow'
start_time = time()
TIMESTAMP = datetime.now()
CHAT_ID = -1001235981203
DEVICE = 'platina'

tree_dir = os.getcwd()

FILENAME = join(tree_dir, f'../lineage-17.1-{TIMESTAMP.strftime("%Y%m%d")}-UNOFFICIAL-platina.zip')
SIGNED_FILENAME = join(tree_dir, f'../lineage-17.1-{TIMESTAMP.strftime("%Y%m%d")}-UNOFFICIAL-platina-signed.zip')

bot = TelegramClient('bot', int(os.environ['API_ID']), os.environ['API_HASH']).start(bot_token=os.environ['TOKEN'])


def update_and_get_tree(s, branch):
    os.chdir(s)
    os.system('git fetch --all')
    os.system('git reset --hard origin/' + branch)
    repo = Repo('.')

    commit_msg = escape_markdown(repo.active_branch.commit.message.split("\n")[0])
    res = f'`{repo.active_branch.name}:' \
          f'`{repo.active_branch.commit.hexsha[:7]}\n' \
          f'`{commit_msg}`'
    os.chdir(tree_dir)
    return res


bot.send_message(CHAT_ID, '⚙️ Build started...\n')
bot.send_message(CHAT_ID, '⚙️ Syncing main tree...\n')
os.system('repo sync --force-sync')

bot.send_message(CHAT_ID, '⚙️ Adding FaceUnlock...\n')
os.system('git clone https://bitbucket.org/syberia-project/external_motorola_faceunlock.git -b 10.0 external/motorola/faceunlock')

def patch(p, link, sha):
    os.chdir(p)
    os.system(f'git fetch {link}')
    os.system(f'git cherry-pick {sha}')
    os.chdir(tree_dir)

patch('vendor/lineage', 'https://github.com/neon-os/vendor_lineage', 'a3f5c3ef14bf8af6bd66104cf108271d414b418c')
patch('frameworks/base', 'https://github.com/neon-os/frameworks_base', 'bc46b8eb130e2b3ce59c4b9adefc028a4459772e')
patch('packages/apps/Settings', 'https://github.com/neon-os/packages_apps_Settings', '7491139bc25f8b1382ab8691b76ed5523fe1d734')

bot.send_message(CHAT_ID, '⚙️ Syncing device trees...\n')
bot.send_message(CHAT_ID, f'⚙️ Device tree commit: {update_and_get_tree("device/xiaomi/platina", "lineage-17.x")}\n'
                          f'  Common device tree commit: {update_and_get_tree("device/xiaomi/sdm660-common", "lineage-17.x")}\n'
                          f'  Vendor tree commit: {update_and_get_tree("vendor/xiaomi/platina", "master")}\n'
                          f'  Common vendor tree commit: {update_and_get_tree("vendor/xiaomi/sdm660-common", "eas")}\n'
                          f'  Kernel commit: {update_and_get_tree("kernel/xiaomi/platina", "staging")}')


def lineage_exec(cmd):
    return os.system(f'bash -c "source build/envsetup.sh; breakfast {DEVICE}; ' + cmd.replace('"', '\\"') + '"')


bot.send_message(CHAT_ID, '⚙️ Building...\n')
if not lineage_exec('mka target-files-package otatools'):
    bot.send_message(CHAT_ID, '⚙️ Signing...\n')
    target_files = glob(f'out/target/product/{DEVICE}/obj/PACKAGING/target_files_intermediates/*-target_files-*.zip')[0]
    lineage_exec(
        './build/tools/releasetools/sign_target_files_apks -o -d '
        f'~/.android-certs {target_files} signed-target_files.zip;'

        './build/tools/releasetools/ota_from_target_files -k ~/.android-certs/releasekey '
        '--block --backup=true signed-target_files.zip ' + SIGNED_FILENAME)
    delta = int(time() - start_time)
    build_time = f'{delta // 60 // 60} hours {delta // 60 % 60} minutes {delta % 60} seconds'
    bot.send_message(CHAT_ID, f'✅ Build succeed in a {build_time}!')
    uploading_msg: Message = bot.send_message(CHAT_ID, '⚙ Uploading, please wait...')
    msg: Message = bot.send_file(CHAT_ID, SIGNED_FILENAME, caption='MD5: `Loading...`', parse_mode='md')
    uploading_msg.delete()
    hash = hashlib.md5()
    with open(SIGNED_FILENAME, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash.update(chunk)
    msg.edit(f'MD5: `{hash.hexdigest()}`', parse_mode='md')
else:
    delta = int(time() - start_time)
    build_time = f'{delta // 60 // 60} hours {delta // 60 % 60} minutes {delta % 60} seconds'
    bot.send_message(CHAT_ID, f'❌ Build failed in a {build_time}!')
