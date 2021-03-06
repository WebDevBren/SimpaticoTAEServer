from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from urlparse import parse_qs
import socket, json
from langdetect import detect

class LexicalSimplifier:

	#Initialize the simplifier handler:
	def __init__(self, host, port):
		self.port = port
		self.host = host

	#Simplify a problem:
	def simplify(self, parameters):
		#Create a simplification request for local lexical simplification server in json format:
		info = {}
		info['sentence'] = parameters['sentence'][0]
		info['target'] = parameters['target'][0]
		info['index'] = parameters['index'][0]
		info['lang'] = parameters['lang'][0]
		data = json.dumps(info)

		try:
			#Send the simplification request to the local server at the designated port:
			s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			s.connect((self.host, self.port))
			s.send(data+'\n')
			
			#Get a response from the server containing the simplified word:
			resp = s.recv(1024).decode('utf8').strip()

			#Close the TCP connection:
			s.close()
			
			if resp=='NULL':
				#If no simplification was found, return an error:
				return {'Error': ['A simplification could not be found.']}
			else:
				#Otherwise, send back a simplification response:
				result = dict(parameters)
				result['target'] = [resp]
				return result
		except Exception as exc:
			#If the connection fails, return an error:
			return {'Error': ['Error while simplifying lexical problem.']}
			
class SyntacticSimplifier:

	#Initialize the simplifier handler:
	def __init__(self, host, port):
		self.port = port
		self.host = host

	#Simplify a problem:
	def simplify(self, parameters):
		#Create a simplification request for local syntactic simplification server in json format:
		info = {}
		info['sentence'] = parameters['sentence'][0]
		info['lang'] = parameters['lang'][0]
		data = json.dumps(info)

		try:
			#Send the simplification request to the local server at the designated port:
			s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			s.connect((self.host, self.port))
			s.send(data+'\n')
			
			#Get a response from the server containing the simplified sentence:
			resp = s.recv(1024).decode('utf8').strip()

			#Close the TCP connection:
			s.close()
			
			if resp=='NULL':
				#If no simplification was found, return an error:
				return {'Error': ['A simplification could not be found.']}
			else:
				#Otherwise, send back a simplification response:
				result = dict(parameters)
				result['sentence'] = [resp]
				return result
		except Exception as exc:
			#If the connection fails, return an error:
			return {'Error': ['Error while simplifying syntactic problem.']}

#This class represents the TAE server handler of Simpatico:
class SimpaticoTAEServer(HTTPServer, object):

	#Initialize the server:
	def __init__(self, *args, **kwargs):
		super(SimpaticoTAEServer, self).__init__(*args, **kwargs)
		self.ls = None
		self.ss = None
	
	#Add a lexical simplifier:
	def addLexicalSimplifier(self, ls):
		self.ls = ls
	
	#Add a syntactic simplifier:
	def addSyntacticSimplifier(self, ss):
		self.ss = ss

#This class represents the TAE server handler of Simpatico:
class SimpaticoTAEHandler(BaseHTTPRequestHandler):
	
	#Handler for the GET requests
	def do_GET(self):
		#Get parameters from URL:
		input_parameters = self.parse_parameters(self.path)
		
		#Detect language:
		try:
			lang = self.correctLanguage(detect(unicode(input_parameters['sentence'][0], 'utf-8')))
		except Exception as exc:
			print 'Error while detecting language.'
			lang = 'en'
			
		#Add it to parameters:
		input_parameters['lang'] = [lang]
		
		#Resolve simplification problem:
		output_parameters = self.simplify(input_parameters)
		
		#Send response:
		self.respond(output_parameters)
		return
	
	#Send a simplification result back to the requester:
	def respond(self, parameters):
		#Send a header:
		self.send_response(200)
		self.send_header('Content-type','application/json')
		self.end_headers()

		#Send the actual simplification response:
		response = json.dumps(parameters)
		self.wfile.write(response)
		return
	
	#Simplify the problem encoded in the parameters:
	#TODO: analyze type of simplification, do a language check (necessary?), call syntactic/lexical simplification, create JSON response, send it back through the function bellow.
	#TODO: check for the existance of an LS and SS simplifiers before simplification.
	def simplify(self, parameters):
		#Report an error:
		if 'Error' in parameters:
			return parameters
		else:
			#Perform a lexical simplification:
			if parameters['type'][0]=='lexical':
				return self.server.ls.simplify(parameters)
			#Perform a syntactic simplification:
			elif parameters['type'][0]=='syntactic':
				return self.server.ss.simplify(parameters)
			#Report an error:
			else:
				return {'Error': ['Value of parameter "type" unknown (available values = "lexical" and "syntactic")']}
	
	#This function parses the parameters of an HTTP request line:
	def parse_parameters(self, text):
		#Parse line:
		try:
			parameters = parse_qs(text[2:])
		except Exception as exc:
			parameters = {'Error': ['Error while parsing problem.']}
		
		#Check for appropriate format:
		#Mandatory parameters:
		# - type = "lexical" or "syntactic"
		#Mandatory LS parameters:
		# - target = the word/phrase to be simplified
		# - sentence = the sentence in which the word was found
		# - index = the position of word in sentence (starts at 0)
		#Mandatory SS parameters:
		# - sentence = the sentence to be simplified
		if 'Error' not in parameters:
			if 'type' not in parameters:
				parameters = {'Error': ['Parameter "type" missing (available values = "lexical" and "syntactic")']}
			elif 'sentence' not in parameters:
				parameters = {'Error': ['Parameter "sentence" missing']}
			elif parameters['type'][0]=='lexical':
				if 'target' not in parameters:
					parameters = {'Error': ['Parameter "target" missing']}
				elif 'index' not in parameters:
					parameters = {'Error': ['Parameter "index" missing']}
		
		#Return final parsed parameters:
		return parameters
	
	#Corrects language detection because of lack of galician support:
	def correctLanguage(self, lang):
		if lang not in set(['en', 'it', 'gl', 'es']):
			return 'gl'
		else:
			return lang

def loadResources(path):
	#Open resource file:
	f = open(path)
	
	#Create resource map:
	resources = {}
	
	#Read resource paths:
	for line in f:
		data = line.strip().split('\t')
		if data[0] in resources:
			print 'Repeated resource name: ' + data[0] + '. Please change the name of this resource.'
		resources[data[0]] = data[1]
	f.close()
	
	#Return resource database:
	return resources			
			
			
			
			
try:
	#Load configurations:
	configurations = loadResources('../configurations.txt')
	
	#Set parameters:
	SERVER_PORT_NUMBER = int(configurations['main_tae_server_port'])
	LS_SERVER = configurations['ls_local_server_host']
	LS_PORT_NUMBER = int(configurations['ls_local_server_port'])
	SS_SERVER = configurations['ss_local_server_host']
	SS_PORT_NUMBER = int(configurations['ss_local_server_port'])

	#Create the lexical simplifier:
	ls = LexicalSimplifier(LS_SERVER, LS_PORT_NUMBER)
	ss = SyntacticSimplifier(SS_SERVER, SS_PORT_NUMBER)
	
	#Create the web server:
	server = SimpaticoTAEServer(('', SERVER_PORT_NUMBER), SimpaticoTAEHandler)
	server.addLexicalSimplifier(ls)
	server.addSyntacticSimplifier(ss)
	
	#Wait forever for incoming simplification requests:
	server.serve_forever()
	
#If Ctrl+C is pressed, then shut down server:
except KeyboardInterrupt:
	server.socket.close()
