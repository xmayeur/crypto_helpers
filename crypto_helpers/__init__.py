from base64 import b64encode, b64decode
from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import MD5
from Crypto.PublicKey import RSA
import sqlite3
import logging
import os

if os.name == 'nt':
    logging.basicConfig(filename='crypto_h.log', level=logging.INFO)
else:
    logging.basicConfig(filename='/var/log/crypto_h.log', level=logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def create_keyset(name='key'):
    key = RSA.generate(2048)
    with open('priv_' + name + '.pem', 'w') as f:
        f.write(key.exportKey('PEM'))
    pubkey = key.publickey()
    with open('pub_' + name + '.pem', 'w') as f:
        f.write(pubkey.exportKey('OpenSSH'))


class Identity:
    
    def __init__(self, db='id.db'):
        self.db = db

        try:
            self.connection = sqlite3.connect(db)
        except sqlite3.Error:
            logging.error('Cannot connect to the database: %s' % self.db)
            
        try:
            cursor = self.connection.cursor()
            sql = '''CREATE TABLE IF NOT EXISTS `id_tbl` (
                    `uid` text NOT NULL,
                    `ID` text NOT NULL,
                    PRIMARY KEY  (`uid`)
                    )
            '''
            cursor.execute(sql)
        except sqlite3.Error:
            logging.error('Cannot create table `id_tbl`')
  
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

    def __enter__(self):
        return self
    
    def close(self):
        self.connection.close()
       
    def add(self, uid, ID):
        try:
            cursor = self.connection.cursor()
            sql = 'INSERT INTO `id_tbl` (`uid`, `ID`) VALUES (?, ?)'
            cursor.execute(sql, (uid, ID))
            self.connection.commit()
            return True
        except sqlite3.Error, e:
            logging.error('Error adding record - %s' % e)
            return False
        
    def update(self, uid, ID):
        try:
            cursor = self.connection.cursor()
            sql = 'UPDATE `id_tbl` SET (`ID`) VALUES (?) WHERE `uid` = ?'
            cursor.execute(sql, (uid, ID))
            self.connection.commit()
            return True
        except sqlite3.Error, e:
            logging.error('Error adding record - %s' % e)
            return False

    def remove(self, uid):
        try:
            cursor = self.connection.cursor()
            sql = "DELETE FROM `id_tbl` WHERE `uid` = ?"
            cursor.execute(sql, (uid, ))
            self.connection.commit()
            return True
        except sqlite3.Error, e:
            logging.error('Error deleting record - %s' % e)
            return False
        
    def fetch(self, uid):
        try:
            cursor = self.connection.cursor()
            sql = "SELECT `ID` FROM `id_tbl` WHERE `uid` = ?"
            cursor.execute(sql, (uid, ))
            return cursor.fetchone()
        except sqlite3.Error, e:
            logging.error('Error fetching record - %s' % e)
            return False


class AEScipher:
    def __init__(self, db='id.db'):
        self.identity = Identity(db)
        self.key = MD5.new(os.path.join(os.getcwd(), db)).digest()
 
    def encrypt(self, text):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return b64encode(iv + cipher.encrypt(text))

    def decrypt(self, msg):
        msg = b64decode(msg)
        iv = msg[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return cipher.decrypt(msg[AES.block_size:])

    def save(self, uid, username, password):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        ID = username + ':' + password
        ID_ = b64encode(iv + cipher.encrypt(ID))
        try:
            self.identity.add(uid, ID_)
        except Exception:
            self.identity.update(uid, ID_)

    def read(self, uid):
        ID_ = self.identity.fetch(uid)[0]
        if ID_ is None:
            return '', ''
        else:
            ID_ = b64decode(ID_)
            iv = ID_[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CFB, iv)
            ID = cipher.decrypt(ID_[AES.block_size:])
            user = ID.split(':')[0]
            pwd = ID.split(':')[1]
            return user, pwd


class RSAcipher:
    def __init__(self, certfile):
        self.key = RSA.importKey(open(certfile).read())
        self.rsa = PKCS1_OAEP.new(self.key)

    def encrypt(self, text):
        return b64encode(self.rsa.encrypt(text))

    def decrypt(self, msg):
        try:
            return self.rsa.decrypt(b64decode(msg))
        except Exception, e:
            return None


def main():
    # text = 'Hello Lobo'
    aes = AEScipher()
    # msg = aes.encrypt(text)
    # if aes.decrypt(msg) == text:
    #     print 'Successful AES encrypt-decrypt'
    #
    # create_keyset('test')
    # rsa = RSAcipher('pub_test.pem')
    # msg = rsa.encrypt(text)
    # rsa = RSAcipher('priv_test.pem')
    # if rsa.decrypt(msg) == text:
    #     print 'Successful RSA encrypt-decrypt'

    user = 'KeyUser'
    pwd = 'KeyPwd123'
    uid ='2'
    
    aes.save(uid, user, pwd)
    user1, pwd1 = aes.read(uid)

    if user == user1 and pwd == pwd1:
        print 'Successful user/pwd store & decode'


if __name__ == "__main__":
    main()