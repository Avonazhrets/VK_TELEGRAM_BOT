import telepot
import time
import vk
from pprint import pprint


bot = telepot.Bot('')
FILE_NAME = 'vk_bot_data'
APPLICATION_ID = ''
VK_API_V = 5.78
GROUP_SHIFT = 2000000000
BASE_USERS = []
BOT_USERNAME = ''


users = dict()


def get_id(msg):
    if 'chat_id' in msg:
        return msg['chat_id'] + GROUP_SHIFT
    else:
        return msg['user_id']


def get_vk_chat_name(msg, vk_api_users):
    if msg['title']:
        return msg['title']
    else:
        return vk_api_users.users.get(user_ids = msg['user_id'], v = VK_API_V)[0]['first_name'] + ' ' + \
               vk_api_users.users.get(user_ids = msg['user_id'], v = VK_API_V)[0]['last_name']


def get_attachment(atch):
    type = atch[0]['type'] + ' :3'
    if type == 'photo':
        type = type + '({})'.format(atch[0]['photo']['sizes'][-1]['url'])
    return type


class User():
    def __init__(self, vk_login, vk_password, tg_id):
        self.vk_login = vk_login
        self.vk_password = vk_password
        self.vk_api_users = vk.API(vk.AuthSession(APPLICATION_ID, vk_login, vk_password, scope = 'users'))
        self.vk_id = int(self.vk_api_users.users.get(v = VK_API_V)[0]['id'])
        self.vk_name = self.vk_api_users.users.get(v = VK_API_V)[0]['first_name'] + ' ' + self.vk_api_users.users.get(v = VK_API_V)[0]['last_name']
        self.tg_id = tg_id
        self.vk_api_msg = vk.API(vk.AuthSession(APPLICATION_ID, vk_login, vk_password, scope = 'messages'))
        self.ban_list = set()
        self.longPollData = self.vk_api_msg.messages.getLongPollServer(need_pts = 1, lp_version = 3, v = VK_API_V)
        self.inbox = dict()
        self.chats = dict()

    def add_chat(self, id, name):
        if not id in self.chats:
            self.chats[id] = name

    def update(self):
        Data = self.vk_api_msg.messages.getLongPollHistory(ts = self.longPollData['ts'], pts = self.longPollData['pts'], v = VK_API_V)
        self.longPollData = self.vk_api_msg.messages.getLongPollServer(need_pts = 1, lp_version = 3, v = VK_API_V)
        for msg in Data['messages']['items']:
            #pprint(msg)
            if msg['out'] == 0 and msg['user_id'] != self.vk_id:
                id = get_id(msg)
                if id in self.ban_list:
                    continue
                if id not in self.inbox:
                    self.inbox[id] = []
                self.inbox[id].append(msg)
                name = get_vk_chat_name(msg, self.vk_api_users)

                self.add_chat(id, name)

                send = 'New message from \'{}\': {}'.format(name, msg['body'])
                if 'attachments' in msg:
                    send = send + ' (' + get_attachment(msg['attachments']) + ')'
                bot.sendMessage(tg_id, send)

    def send_msg(self, ch_id, text):
        if ch_id >= GROUP_SHIFT:
            self.vk_api_msg.messages.send(chat_id = ch_id - GROUP_SHIFT, message = text, v = VK_API_V)
        else:
            self.vk_api_msg.messages.send(user_id = ch_id, message = text, v = VK_API_V)

    def add_to_ban_list(self, chat_name):
        for chat_id in self.chats:
            if self.chats[chat_id] == chat_name:
                if chat_id in self.ban_list:
                    raise ValueError('Already inserted!')
                self.ban_list.add(chat_id)
                self.inbox[chat_id].clear()
                return
        raise TypeError('No such chat')

    def remove_from_ban_list(self, chat_name):
        for chat_id in self.chats:
            if self.chats[chat_id] == chat_name:
                if chat_id not in self.ban_list:
                    raise ValueError('Already removed!')
                self.ban_list.remove(chat_id)
                return
        raise TypeError('No such chat')



def recollect_data():
    global users
    users = {}
    try:
        fin = open(FILE_NAME, 'r')
        all_data = fin.readlines()
        for i in all_data:
            tg_id, vk_lg, vk_ps = i.strip().split()
            tg_id = int(tg_id)
            users[tg_id] = User(vk_lg, vk_ps, tg_id)
        fin.close()
    except:
        pass


def print_data():
    try:
        file = open(FILE_NAME, 'r')
        all_data = file.readlines()
        for i in all_data:
            tg_id, vk_lg, vk_ps = i.strip().split()
            print(tg_id + ' ' + vk_lg + ' ' + vk_ps)
        file.close()
    except:
        pass


def add_data():
    global users
    fout = open(FILE_NAME, 'w')
    for tg_id in users:
        fout.write('{} {} {}\n'.format(tg_id, users[tg_id].vk_login, users[tg_id].vk_password))
    fout.close()


def check_login_password(login, password):
    try:
        vk.AuthSession(APPLICATION_ID, login, password)
        return True
    except:
        return False


def login(msg):
    try:
        cmd, vk_login, vk_password = msg['text'].split()
        tg_id = int(msg['chat']['id'])
        users[tg_id] = User(vk_login, vk_password, tg_id)
        add_data()
        first_name = vk.API(vk.AuthSession(APPLICATION_ID, vk_login, vk_password, scope = 'users')).users.get(v = VK_API_V)[0]['first_name']
        last_name = vk.API(vk.AuthSession(APPLICATION_ID, vk_login, vk_password, scope = 'users')).users.get(v = VK_API_V)[0]['last_name']
        bot.sendMessage(msg['chat']['id'], 'Hello, {} {}! You\'re successfully logged in!'.format(first_name, last_name))
    except:
        bot.sendMessage(msg['chat']['id'], 'Something is wrong')


def check_prefix(text, cmd):
    return text.split()[0] == cmd

def push_user(tg_id):
    for id in BASE_USERS:
        if id != tg_id:
            vk_api = vk.API(vk.AuthSession(APPLICATION_ID, users[tg_id].vk_login, users[tg_id].vk_password, scope = 'messages'))
            vk_api.messages.send(user_id = users[id].vk_id, message = 'Го в тг', v = VK_API_V)


def cut_name_from_bot_msg(msg):
    return msg['reply_to_message']['text'].split('\'')[1]


def reply_to_chat(msg):
    if 'reply_to_message' not in msg or msg['reply_to_message']['from']['username'] != BOT_USERNAME:
        bot.sendMessage(msg['chat']['id'], 'Something is wrong')
        return
    try:
        user_name = cut_name_from_bot_msg(msg)
        tg_id = int(msg['chat']['id'])
        for id in users[tg_id].chats:
            if users[tg_id].chats[id] == user_name:
                users[tg_id].send_msg(id, ' '.join(msg['text'].split()[1:]))
                users[tg_id].inbox[id].clear()
                bot.sendMessage(msg['chat']['id'], '{} received your message'.format(user_name))
    except:
        bot.sendMessage(msg['chat']['id'], 'Something is wrong, I guess')


def ban_msg_from_chat(msg):
    try:
        chat_name = ''
        if 'reply_to_message' in msg:
            chat_name = cut_name_from_bot_msg(msg)
        else:
            bot.sendMessage(msg['chat']['id'], 'You need to reply to a message')
            return
        users[msg['chat']['id']].add_to_ban_list(chat_name)
        bot.sendMessage(msg['chat']['id'], '{} has been successfully added to ban list'.format(chat_name))
    except ValueError:
        bot.sendMessage(msg['chat']['id'], 'Already in the ban list')
    except TypeError:
        bot.sendMessage(msg['chat']['id'], "No such chat")
    except:
        bot.sendMessage(msg['chat']['id'], 'Something is wrong, I guess')


def allow_msg_from_chat(msg):
    try:
        chat_name = ''
        if 'reply_to_message' in msg:
            chat_name = cut_name_from_bot_msg(msg)
        else:
            bot.sendMessage(msg['chat']['id'], 'You need to reply to a message')
            return
        users[msg['chat']['id']].remove_from_ban_list(chat_name)
        bot.sendMessage(msg['chat']['id'], '{} has been successfully removed from ban list'.format(chat_name))
    except ValueError:
        bot.sendMessage(msg['chat']['id'], 'Already allowed')
    except TypeError:
        bot.sendMessage(msg['chat']['id'], "No such chat")
    except:
        bot.sendMessage(msg['chat']['id'], 'Something is wrong, I guess')


def handle(msg):
    print("kek")
    pprint(msg)
    tg_id = int(msg['chat']['id'])
    if check_prefix(msg['text'], '/login'):
        login(msg)
    elif check_prefix(msg['text'], '/push'):
        push_user(msg['chat']['id'])
    elif check_prefix(msg['text'], '/reply'):
        reply_to_chat(msg)
    elif check_prefix(msg['text'], '/ban'):
        ban_msg_from_chat(msg)
    elif check_prefix(msg['text'], '/allow'):
        allow_msg_from_chat(msg)
    else:
        if tg_id not in users:
            bot.sendMessage(msg['chat']['id'], 'Please, enter your login and password using /login')
        elif not check_login_password(users[tg_id].vk_login, users[tg_id].vk_password):
            bot.sendMessage(msg['chat']['id'], 'Your login or password seems to be invalid. Please, re-enter it using /login')
        else:
            bot.sendMessage(msg['chat']['id'], 'Everything is OK!')



recollect_data()
bot.message_loop(handle)


while True:
    time.sleep(2)
    for tg_id in users:
        users[tg_id].update()

