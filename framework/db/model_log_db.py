import os
import time
import socket
try:
	import pyodbc
except:
	print("FAILED TO IMPORT PYODBC.  INSTALL PYODBC FOR LOGGING!")

connection_string = "Driver={ODBC Driver 13 for SQL Server};" \
										"Server=modelrepo.database.windows.net;" \
										"Database=model_repo;" \
										"UID=thduon;PWD=m0del_rep0;"


class ModelLogDbWriter:
	_all_objects = []

	def connect(self, constr):
		for retry in range(3):
			try:
				self._db = pyodbc.connect(constr)
				return
			except Exception as e:
				print(e)
				print("WARNING: FAILED TO CONNECT TO DATABASE")
				self._db = None
				continue

	def __init__(self, con_string = connection_string):
		self._connection_string = con_string
		self.connect(self._connection_string)
		self._id = -1
		self._done = True
		ModelLogDbWriter._all_objects.append(self)

	def begin_training(self, model_name, output_location):
		if self._db is None:
			self.connect(self._connection_string)
			return
		cursor = self._db.cursor()
		training_gpu_env = ''
		if 'CUDA_VISIBLE_DEVICES'  in os.environ:
			training_gpu_env = os.environ['CUDA_VISIBLE_DEVICES']
		training_host = socket.gethostname()
		model_name = model_name
		pid = os.getpid()
		public_ip = os.popen('curl ifconfig.me -s').read().rstrip().lstrip()
		sql = "INSERT INTO [dbo].[model_training] " \
		"([model_name], [training_start], [training_host], [training_gpu_env], [training_pid], [training_host_ip], [training_state], [output_location],[training_start_time_epoch]) " \
		" VALUES " \
					"('%s',CURRENT_TIMESTAMP,'%s','%s',%s,'%s',0,'%s',%s)" \
					%(model_name, training_host, training_gpu_env, pid, public_ip, output_location,time.time())
		cursor.execute(sql)
		self._done = False
		self._db.commit()

		cursor.execute("SELECT SCOPE_IDENTITY()")
		row = cursor.fetchone()
		self._id = row[0]
		return self._id

	def set_training_state(self, state):
		self.update_db({'training_state':state,'training_state_change_time':'CURRENT_TIMESTAMP'})

	def update_db(self, entries):
		if self._db is None:
			self.connect(self._connection_string)
			return
		for retry in range(3):
			try:
				cursor = self._db.cursor()
				entries['last_update_time_epoch'] = time.time()
				update_fields = ""
				for key, value in entries.items():
					if len(update_fields) > 0:
						update_fields += ","
					if isinstance(value,str) and not(value=="CURRENT_TIMESTAMP"):
						update_fields += "%s='%s'"%(key,value)
					else:
						update_fields += "%s=%s"%(key,value)
				sql = "update [dbo].[model_training] SET %s WHERE id=%s"%(update_fields,self._id)
				cursor.execute(sql)
				self._db.commit()
				return
			except pyodbc.Error as e:
				sqlstate = e.args[0]
				if sqlstate == '08S01':
					print("CONNECTION BROKEN!  RECONNECTING!")
					self.connect(self._connection_string)
					continue
				continue
			except:
				print("Exception")
				print("SQL: %s"%sql)
				continue

	def on_update(self, epoch, minibatch, iteration_count, loss, log_line):
		self.update_db({'epoch':epoch,'minibatch':minibatch, 'iteration_count':iteration_count,
										'last_loss':loss, 'last_training_log_line':log_line,'last_update':'CURRENT_TIMESTAMP'})

	def done_training(self):
		self.update_db({'training_state':10,'training_state_change_time':'CURRENT_TIMESTAMP'})
		self._done = True

	def __del__(self):
		ModelLogDbWriter._all_objects.remove(self)

	def on_checkpoint_saved(self, save_path):
		self.update_db({'last_checkpoint_time':'CURRENT_TIMESTAMP'})

	def _at_exit(self):
		# update exit time
		if not self._done:
			self.update_db({'training_state':9,'training_state_change_time':'CURRENT_TIMESTAMP'})

	@staticmethod
	def _static_at_exit():
		for o in ModelLogDbWriter._all_objects:
			o._at_exit()

import atexit
atexit.register(ModelLogDbWriter._static_at_exit)



class ModelLogDbViewer:

	def connect(self, constr):
		for retry in range(3):
			try:
				self._db = pyodbc.connect(constr)
				return
			except Exception as e:
				print(e)
				print("WARNING: FAILED TO CONNECT TO DATABASE")
				self._db = None
				continue

	def __init__(self, con_string = connection_string):
		self._connection_string = con_string
		self.connect(self._connection_string)

	def get_all_trainers(self):
		if self._db is None:
			self.connect(self._connection_string)
			return [],[]
		for retry in range(3):
			try:
				cursor = self._db.cursor()
				cursor.execute("SELECT * FROM [dbo].[model_training]")
				columns = [column[0] for column in cursor.description]
				return cursor.fetchall(), columns
			except pyodbc.Error as e:
				sqlstate = e.args[0]
				if sqlstate == '08S01':
					print("CONNECTION BROKEN!  RECONNECTING!")
					self.connect(self._connection_string)
					continue
				continue
			except:
				print("Exception")
				print("SQL: %s"%sql)
				continue



if __name__ == "__main__":
	db = ModelLogDbWriter()
	params = {'model_name':'testing'}
	db.begin_training("mymodel","test")
	db.done_training()



	"""
	/****** Object:  Table [dbo].[model_training]    Script Date: 1/31/2018 8:32:39 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[model_training](
	[id] [int] IDENTITY(0,1) NOT NULL,
	[model_name] [varchar](max) NULL,
	[training_start] [datetime] NULL,
	[training_host] [varchar](max) NULL,
	[training_host_ip] [varchar](max) NULL,
	[training_gpu_env] [varchar](max) NULL,
	[last_checkpoint_time] [datetime] NULL,
	[training_pid] [int] NULL,
	[last_update] [datetime] NULL,
	[last_loss] [float] NULL,
	[last_training_log_line] [varchar](max) NULL,
	[training_should_stop] [int] NULL,
	[training_state] [int] NULL,
	[training_state_change_time] [datetime] NULL,
	[output_location] [varchar](max) NULL,
	[epoch] [int] NULL,
	[minibatch] [int] NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO



	"""
