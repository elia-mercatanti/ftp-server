# Author: Elia Mercatanti
# Matricola: 5619856
# Implementazione senza thread - Assumo che il server gestisca un solo cliente alla volta. Il server rimane in
# esecuzione finche il suo processo non viene terminato.

import os
import socket
import platform
import time

# Indirizzo ip e porta del server
server_ip = ''
server_port = 10000

# Dizionaro per dati utenti -- username: password, absolutePath
userData = {'user1': ('pwd1', '/tmp/home1'), 'user2': ('pwd2', '/tmp/home2'), 'Elia': ('pass', '/tmp/home3')}

# Root directory per dell'FTP server - In questo caso 'tmp' e' la cartella radice del server
serverBaseDir = os.path.realpath('/tmp')

class MyFtpServer:
    # Inizializza le strutture dati usate dal server
    def __init__(self, userdata, port):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((server_ip, port))
        self.dataSocket = None
        self.dataAddress = None
        self.dataPort = 20
        self.passiveSocket = None
        self.bufferSize = 1024
        self.userData = userdata
        self.login = False
        self.currentUser = ''
        self.rootDir = serverBaseDir
        self.currentDir = self.rootDir
        self.end = False
        self.connection = False
        self.pasv_mode = False
        self.type = 'A N'

    # Avvia il server
    def start(self):
        # Imposto la connessione al client
        self.serverSocket.listen(1)

        # Ciclo per connessione
        while (self.end == False):
            print 'The server is ready to receive\n'
            self.connectionSocket, self.addr = self.serverSocket.accept()

            self.connection = True
            cmd = ''
            # Messaggio di benvenuto
            self.connectionSocket.send('220 Welcome to MyFTPServer!\r\n')

            # Ciclo principale
            while self.connection == True:
                # Ricevo comando dal client
                try:
                    cmd = cmd + self.connectionSocket.recv(self.bufferSize)
                except socket.error:
                    print "An existing connection was forcibly closed by the remote host.\n"
                    self.login = False
                    self.currentUser = ''
                    self.currentDir = self.rootDir
                    self.connection = False;
                    break
                if not cmd:
                    print "An error has occurred when tryin to receive a command.\n"
                    self.connection = False;
                    break

                elif cmd.endswith('\n'):
                    print 'Command recieved:', cmd
                    # Controllo quale comando l'utente ha inserito, altrimenti lancio un eccezione per comando errato
                    try:
                        func = getattr(self, cmd.split()[0].upper())
                        func(cmd)
                        cmd = ''
                    except (AttributeError, IndexError):
						if(self.login == False):
							self.syntax_command_error(3)
						else:
							self.syntax_command_error(0)
                        cmd = ''

    # Funzione che gestisce l'invio di messaggi di errore generici
    def syntax_command_error(self, type):
        if type == 0:
            self.connectionSocket.send('500 Syntax Error. Unrecognized command.\r\n')
        elif type == 1:
            self.connectionSocket.send('501 Syntax error in parameters or arguments.\r\n')
        elif type == 2:
            self.connectionSocket.send('503 Bad sequence of commands.\r\n')
        elif type == 3:
            self.connectionSocket.send('530 Not logged in.\r\n')
        elif type == 4:
            self.connectionSocket.send('331 Username ok. Insert the password.\r\n')

    # Funzione per il controllo sulle directory accessibili
    def is_sub_path(self, path, sub_path):
        if sub_path.startswith(path):
            return True
        else:
            return False

    def USER(self, cmd):
        if len(cmd.split()) != 2:
            self.syntax_command_error(1)
        else:
            if not self.login:
                self.currentUser = cmd.split()[1]
                self.connectionSocket.send('331 Username Ok. Password required for \'' + self.currentUser + '\'.\r\n')
            elif cmd.split()[1] == self.currentUser:
                self.connectionSocket.send('331 Username Ok.\r\n')
            else:
                self.connectionSocket.send('530 Wrong logged user.\r\n')

    def PASS(self, cmd):
        if self.currentUser == '':
            self.syntax_command_error(2)
        elif len(cmd.split()) != 2:
            self.syntax_command_error(1)
        elif self.login:
            self.connectionSocket.send('230 Passowrd Ok.\r\n')
        else:
            if self.currentUser in self.userData and cmd.split()[1] == self.userData[self.currentUser][0]:
                self.login = True
                self.currentDir = os.path.realpath(self.userData[self.currentUser][1])
                self.connectionSocket.send('230 User ' + self.currentUser + ' logged in.\r\n')
            else:
                self.connectionSocket.send('530 Login incorrect. You provided the wrong username/password.\r\n')
                self.currentUser = ''

    def SYST(self, cmd):
        if len(cmd.split()) != 1:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            self.connectionSocket.send('215 ' + platform.system() + ' Type: L8.\r\n')

    def FEAT(self, cmd):
        if len(cmd.split()) != 1:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            self.connectionSocket.send('211 \r\n')

    def PWD(self, cmd):
        if len(cmd.split()) != 1:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            self.currentDir = os.path.realpath(self.currentDir)
            self.connectionSocket.send('257 "%s"\r\n' % (self.currentDir))

    def NOOP(self, cmd):
        if not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            self.connectionSocket.send('200 Ok.\r\n')

    def QUIT(self, cmd):
        self.login = False
        self.currentDir = self.rootDir
        self.connectionSocket.send('221 Goodbye ' + self.currentUser +'!\r\n')
        self.currentUser = ''
		self.pasv_mode = False
        self.connectionSocket.close()
        self.connection = False

    # Lavora su path assoluti
    def CWD(self, cmd):
        if len(cmd.split()) != 2:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            new_path = (cmd.split()[1])
            if not os.path.isabs(new_path):
                new_path=os.path.join(self.currentDir, new_path)
                new_path = os.path.realpath(new_path)

            user_root_path = os.path.realpath(self.userData[self.currentUser][1])
            if os.path.isdir(os.path.realpath(new_path)) and self.is_sub_path(user_root_path, new_path):
                self.currentDir = new_path
                self.connectionSocket.send('250 The working directory has been changed correctly.\r\n')
            else:
                self.connectionSocket.send('550 Requested action not taken.\r\n')

    def CDUP(self, cmd):
        if len(cmd.split()) != 1:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            user_root_path = os.path.realpath(self.userData[self.currentUser][1])
            if self.currentDir != user_root_path:
                self.currentDir = os.path.realpath(os.path.join(self.currentDir,'..'))
                self.connectionSocket.send('250 The working directory has been changed correctly.\r\n')
            else:
                self.connectionSocket.send('550 Requested action not taken.\r\n')

    def PORT(self, cmd):
        if len(cmd.split()) != 2:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        elif self.pasv_mode:
            self.passiveSocket.close()
            self.pasv_mode = False
        else:
            port_parameters = cmd.split()[1].split(',')
            if len(port_parameters) != 6:
                self.syntax_command_error(0)
            else:
                ip_fields = port_parameters[:4]
                port_fields = port_parameters[4:]

                # Cotrollo che tutti i parametri inseriti siano degli interi
                try:
                    for field in ip_fields:
                        int(field)
                    for field in port_fields:
                        int(field)

                    self.dataAddress = ".".join(ip_fields)
					port = int(port_fields[0]) * 256 + int(port_fields[1])
					
					if port > 2**16 - 1:
						self.connectionSocket.send('500 Invalid port number.\r\n')
					else:
						self.dataPort = port
						self.connectionSocket.send('200 PORT command successful.\r\n')
                except ValueError:
                    self.connectionSocket.send('500 Error in arguments type.\r\n')

    def start_data_socket(self):
        if self.pasv_mode:
            self.dataSocket, clientAddr = self.passiveSocket.accept()
            print 'Passive connection to:', clientAddr
        else:
            self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.dataSocket.connect((self.dataAddress, self.dataPort))

    def stop_data_socket(self):
        self.dataSocket.close()
        if self.pasv_mode:
            self.passiveSocket.close()

    def LIST(self, cmd):
        if len(cmd.split()) > 2:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        elif self.dataAddress is None and not self.pasv_mode:
            self.connectionSocket.send('425 Can\'t open data connection. Require PORT or PASV command first.\r\n')
        else:
            if len(cmd.split()) == 1:
                path = self.currentDir
            elif not os.path.isabs(cmd.split()[1]):
                path = os.path.join(self.currentDir, cmd.split()[1])
                path = os.path.realpath(path)
            else:
                path = os.path.realpath(cmd.split()[1])

            user_root_path = os.path.realpath(self.userData[self.currentUser][1])

            if (os.path.isdir(path) or os.path.isfile(path)) and self.is_sub_path(user_root_path, path):
                # Apro la connessione dati
                try:
                    self.connectionSocket.send('150 Opening data connection.\r\n')
                    self.start_data_socket()

                    for entries in os.listdir(path):
                        line = self.to_list_item(os.path.join(path, entries))
                        self.dataSocket.send(line + '\r\n')

                    self.stop_data_socket()
                    self.connectionSocket.send('226 Transfer complete.\r\n')
                except socket.error:
                    self.connectionSocket.send('425 Can\'t open data connection.\r\n')
            else:
                self.stop_data_socket()
                self.connectionSocket.send('550 Requested action not taken. Path unavailable.\r\n')

    # I parametri user e group in windows non possono essere recuperati con le librerie standard di python quindi la
    # funzione per quei parametri ritorna semplicemente 'user group'
    def to_list_item(self, item):
        stat = os.stat(item)
        fullmode = 'rwxrwxrwx'
        mode = ''
        for i in range(9):
            mode += ((stat.st_mode >> (8-i)) & 1) and fullmode[i] or '-'
        d = (os.path.isdir(item)) and 'd' or '-'
        ftime = time.strftime(' %b %d %H:%M ', time.gmtime(stat.st_mtime))
        return d + mode + ' ' + str(stat.st_nlink) + ' user group ' + str(stat.st_size) + ' ' + ftime + \
               os.path.basename(item)

    def PASV(self, cmd):
        if len(cmd.split()) != 1:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        else:
            self.pasv_mode = True
            self.passiveSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.passiveSocket.bind((server_ip, 0))
            self.passiveSocket.listen(1)
            ip, port = self.passiveSocket.getsockname()
            print 'Open passive mode:', ip, port
            self.connectionSocket.send('227 Entering Passive Mode (%s,%u,%u).\r\n' % (','.join(ip.split('.')),
                                                                                      port >> 8&0xFF, port&0xFF))

    def TYPE(self, cmd):
        cmd = cmd.split()
        if len(cmd) > 3 or len(cmd) == 1:
            self.syntax_command_error(1)
            return
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
            return
        elif not self.login:
            self.syntax_command_error(3)
            return
        elif cmd[1] == 'A' and len(cmd) == 3:
            type_char = cmd[2]
            if type_char == 'N' or type_char == 'T' or type_char == 'C':
                self.type = 'A ' + type_char
            else:
                self.connectionSocket.send('500 Error in arguments type.\r\n')
                return
        else:
            if cmd[1] == 'A':
                self.type = 'A N'
            elif cmd[1] == 'I':
                self.type = cmd[1]
            else:
                self.connectionSocket.send('500 Error in arguments type.\r\n')
                return
        self.connectionSocket.send('200 Command okay. Type ' + self.type + '.\r\n')

    def RETR(self,cmd):
        if len(cmd.split()) != 2:
            self.syntax_command_error(1)
        elif not self.login and self.currentUser:
            self.syntax_command_error(4)
        elif not self.login:
            self.syntax_command_error(3)
        elif self.dataAddress is None and not self.pasv_mode:
            self.connectionSocket.send('425 Can\'t open data connection. Require PORT or PASV command first.\r\n')
        else:
            # file_path = os.path.realpath(cmd.split()[1])
            file_path = cmd.split()[1]
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.currentDir, file_path)
                file_path = os.path.realpath(file_path)
            else:
                file_path = os.path.realpath(file_path)

            user_root_path = os.path.realpath(self.userData[self.currentUser][1])
            if os.path.isfile(file_path) and self.is_sub_path(user_root_path, file_path):
                print 'Downlowding file:', file_path

                # Controllo in che modo aprire il file
                if self.type == 'I':
                    file_desc = open(file_path, 'rb')
                    fmode = 'BINARY'
                else:
                    file_desc = open(file_path, 'r')
                    fmode = 'DEFAULT'

                try:
                    self.connectionSocket.send('150 Opening ' + fmode + ' mode data connection for ' +
                                           os.path.basename(file_path) + '.\r\n')
                    # Leggo e invio il file
                    data = file_desc.read(self.bufferSize)
                    self.start_data_socket()
                    while data:
						data = data.replace('\n', '\r\n')
                        self.dataSocket.send(data)
                        data = file_desc.read(self.bufferSize)
                    file_desc.close()
                    self.stop_data_socket()
                    self.connectionSocket.send('226 Transfer complete.\r\n')
                except socket.error:
                    self.connectionSocket.send('425 Can\'t open data connection.\r\n')
                except IOError:
                    self.connectionSocket.send('451 Requested action aborted. Can\'t read the file.\r\n')
            else:
                self.stop_data_socket()
                self.connectionSocket.send('550 Requested action not taken. File unavailable.\r\n')