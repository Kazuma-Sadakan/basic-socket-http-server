import socket, signal
import sys, os, io
import errno, logging

from logger import logger

BUFFER_SIZE = 1024
HOST = '127.0.0.1'
PORT = 7000

class Server(object):
    def __init__(self, address = ('127.0.0.1', 7000), 
                protocol = socket.IPPROTO_TCP, 
                request_size = socket.SOMAXCONN):
        try:
            for res in socket.getaddrinfo(host = address[0], port = address[1], family = socket.AF_INET, 
                                        type = socket.SOCK_STREAM, proto = protocol, 
                                        flags = socket.AI_PASSIVE):
                family, type, protocol, canoname, address = res
            logger.info(f"getaddrinfo: socket address info returned")

        except socket.gaierror as e:
            logger.critical(f"getaddrinfo: {e}")
            sys.exit(1)

        try:
            # Create a TCP/IP socket 
            self.socket = socket.socket(family, type, protocol)
            logger.info(f"socket: socket is created")
        except OSError as e:
            logger.critical(f"socket: {e}")
            sys.exit(1)

        try:
            ip, port = socket.getnameinfo(address, socket.AI_PASSIVE)
            logger.info(f"getnameinfo: socket name info is returned")
        except socket.gaierror as e:
            logger.critical(f"getnameinfo: {e}")
            sys.exit(1)
        
        try:
            # Make the same address reusable 
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind the socket to the port 
            self.socket.bind(address)
            logger.info(f"socketbind: socket is binded")
        except OSError as e:
            logger.warning(f"bind: {e}")
            self.socket.bind((self.HOST, self.PORT))
            
        finally:
            self.address = self.socket.getsockname()
            self.server_name = socket.getfqdn(self.address[0])
            # Activate the server
            try:
                self.socket.listen(request_size)
                logger.info(f"Server: {self.server_name} is running on port {self.address[1]}...")
            except OSError as e:
                logger.critical(f"listen: {e}")
                self.socket.close()
                sys.exit(1)

        self.headers_set = []
        self.headers_sent = []
        self.application = None

    def server_forever(self):
        def handler(signum, frame):
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                logger.info(f"{pid} terminated with {status}")
            except OSError as e:
                logger.debug(f"handler: {e}")
                return
            if pid == 0:
                return
        signal.signal(signal.SIGCHLD, handler)

        while True:
            try:
                # Wait for a new connection
                (client_socket, client_address) = self.socket.accept()
                logger.info(f"getnameinfo: socket is accepting new clients")
                print(f"{client_address[0]}:{client_address[1]} is accepted")
            except IOError as e:
                logger.warning(f"accept: {e}")
                code, msg = e.args
                if code == errno.EINTR:
                    continue 
                else:
                    break

            except InterruptedError as e:
                logger.warning(f"accept: {e}")
                continue

            except KeyboardInterrupt as e:
                logger.warning(f"accept: {e}")
                logger.info("\nShutting down...")
                break
            
            pid = os.fork() #fork to eliminate blocking of each client process
            logger.info("forked successfuly")
            
            if pid == 0: # child process 
                self.socket.close()
                logger.info("socket in child fork closed successfuly")
                print(client_socket)
                try:     
                    request_data = self.receive_loop(client_socket)
                    print(request_data)
                    method, path, protocol, headers, body = self.parse_http(request_data)
                    env = self.get_environ(method, path, protocol, body)
                    response_body = self.application(env, self.start_response)
                    logger.info("############",response_body)
                    try:
                        for chunk in response_body:
                            self.write(chunk)
                            logger.info("successfuly wrote response_body")
                            self.response(client_socket, chunk)
                            logger.info("successfuly respond to the client")
                    except Exception as e:
                        logger.debug(f"respond: {e}")
                    finally:
                        if hasattr(response_body, "close"):
                            response_body.close()
                    
                    # kill the client socket connection
                    # client_socket.shutdown(socket.SHUT_WR)
                    client_socket.close()
                    os._exit(0)

                except Exception as e:
                    logger.debug("couldn't respond to the client")
                    os._exit(1)
                
            else:
                
                try:
                    client_socket.close()
                    logger.info("client socket in the parent fork closed successfuly")
                except Exception as e:
                    logger.debug("couldn't close the client socket in the parent fork")
                
        self.socket.close()

    def set_app(self, app):
        self.application = app

    def receive_loop(self, client_socket):
        buffer = bytes()
        while True:
            try:
                request_data = client_socket.recv(BUFFER_SIZE)
                
                buffer += request_data
                
                logger.info("successfully accepted request data")
                
            except IndentationError as e:
                logger.debug(f"recv: {e}")
                break
            
            except Exception as e:
                logger.debug(f"receive_roop: {e}")

            if b"\r\n\r\n" in buffer:
                _, _, _, headers, body = self.parse_header(buffer)
                
                if int(headers.get("Content-Length", 0)) > len(body):
                    continue

                else:
                    logger.info("recv: [EOF]")
                    # client_socket.close()
                    break
        return buffer
        
    def parse_http(self, http):
        method, path, protocol, headers, body = self.parse_header(http)
        body = self.parse_body(method, headers.get("Content-Length", 0), body)
        return method, path, protocol, headers, body

    def parse_header(self, request_data):
        print("###continue")
        try:
            request, *headers, _, body = request_data.split(b"\r\n")
            method, path, protocol = request.decode("utf-8").split(" ")
            headers = dict(
                line.decode("utf-8").split(":", maxsplit=1) for line in headers
            )
            logger.info(f"successfuly extracted http request header")
        except Exception as e:
            logger.debug(f"parse_http:{e}")

        return method, path, protocol, headers, body

    def parse_body(self, method, length, body):
        if method == "POST":
            try:
                assert int(length) == len(body)
                body = {key: val for key, val in [el.split("=") for el in body.decode('utf-8').split("&")]}
                logger.info(f"successfuly extracted http request body")
            except AssertionError as e:
                logger.critical("body length: {e}")
                sys.exit(1)

        return body

    def write(self, response_body):
        if not self.headers_set:
            raise AssertionError("write() occured before start_response")
        
        elif not self.headers_sent:
            status, headers = self.headers_sent[:] = self.headers_set
            sys.stdout.write(f"{status}\r\n")
            for header in headers:
                sys.stdout.write("{0}: {1}\r\n".format(*header))
            sys.stdout.write("\r\n")
        sys.stdout.write(response_body.decode("utf-8"))
        sys.stdout.flush()

        
    def get_environ(self, method, path, protocol, body):
        # env = dict(os.environ.items())
        env = {}

        # Set WSGI variables 
        env["wsgi.version"] = (1.0)
        env["wsgi.input"] = io.BytesIO(body) #<_io.BytesIO>
        # env["wsgi.input"] = sys.stdin
        env["wsgi.errors"] = sys.stderr
        env["wsgi.multithread"] = False
        env["wsgi.multiprocess"] = True
        env["wsgi.run_once"] = True

        if env.get("HTTPS", "off") in ("on", "1"):
            env["wsgi.url_scheme"] = "https"
        else:
            env["wsgi.url_scheme"] = "http"

        # Set CGI vatiables 

        env["REQUEST_METHOD"] = method
        env["SCRIPT_NAME"] = ""
        env["PATH_INFO"] = path
        env["QUERY_STRING"] = ""
        env["CONTENT_LENGTH"] = ""
        env["SERVER_PROTOCOL"] = protocol
        env["SERVER_NAME"] = self.server_name
        env["SERVER_PORT"] = str(self.address[1])
        # env["HTTP_{}".format()] = ""
        logger.info("successfuly returned env")
        return env

    def start_response(self, status, response_headers, exc_info=None):
        print("start_response")
        # exc_info is to send back some data to server from an application
        # this function doesn't send the headers to clients, but from the application
        if exc_info:
            try:
                if self.headers_set:      
                    raise exc_info[0]
            finally:
                exc_info = None
        elif self.headers_set:
            raise AssertionError("headers is already set")
        logger.info("start_response succeeded")
        self.headers_set[:] = [status, response_headers]
        return self.write

    def response(self, client_socket, response_body):
        try:
            status, headers = self.headers_sent
            response_ = f"HTTP/1.1 {status}\r\n"
            
            for header in headers:
                response_ += "{0}: {1}\r\n".format(*header)
            
            response_ += "\r\n" # end of the header
            response_ += response_body.decode('utf-8')
            print(len(response_body.decode('utf-8')))
            print(response_)
            client_socket.sendall(response_.encode())
        except Exception as e:
            print(f"response: {e}")