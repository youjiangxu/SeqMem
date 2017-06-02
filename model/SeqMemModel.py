import os
# os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   # see issue #152

import tensorflow as tf

import numpy as np
import InitUtil

rng = np.random
rng.seed(1234)

def hard_sigmoid(x):
	x = (0.2 * x) + 0.5
	x = tf.clip_by_value(x, tf.cast(0., dtype=tf.float32),tf.cast(1., dtype=tf.float32))
	return x





class SeqMemAttentionModel(object):
	'''
		caption model for ablation studying
	'''
	def __init__(self, input_feature, input_captions, voc_size, d_w2v, output_dim, attention_dim = 100, dropout=0.5,
		inner_activation='hard_sigmoid',activation='tanh',
		return_sequences=True):
		self.input_feature = input_feature
		self.input_captions = input_captions

		self.voc_size = voc_size
		self.d_w2v = d_w2v
		self.output_dim = output_dim
		self.dropout = dropout

		self.inner_activation = inner_activation
		self.activation = activation
		self.return_sequences = return_sequences
		self.attention_dim = attention_dim

		self.encoder_input_shape = self.input_feature.get_shape().as_list()
		self.decoder_input_shape = self.input_captions.get_shape().as_list()
	def init_parameters(self):
		print('init_parameters ...')

		# encoder parameters
		# print(self.encoder_input_shape)
		encoder_i2h_shape = (self.encoder_input_shape[-1],self.output_dim)
		encoder_h2h_shape = (self.output_dim,self.output_dim)
		self.W_e_r = InitUtil.init_weight_variable(encoder_i2h_shape,init_method='glorot_uniform',name="W_e_r")
		self.W_e_z = InitUtil.init_weight_variable(encoder_i2h_shape,init_method='glorot_uniform',name="W_e_z")
		self.W_e_h = InitUtil.init_weight_variable(encoder_i2h_shape,init_method='glorot_uniform',name="W_e_h")

		self.U_e_r = InitUtil.init_weight_variable(encoder_h2h_shape,init_method='orthogonal',name="U_e_r")
		self.U_e_z = InitUtil.init_weight_variable(encoder_h2h_shape,init_method='orthogonal',name="U_e_z")
		self.U_e_h = InitUtil.init_weight_variable(encoder_h2h_shape,init_method='orthogonal',name="U_e_h")

		self.b_e_r = InitUtil.init_bias_variable((self.output_dim,),name="b_e_r")
		self.b_e_z = InitUtil.init_bias_variable((self.output_dim,),name="b_e_z")
		self.b_e_h = InitUtil.init_bias_variable((self.output_dim,),name="b_e_h")

		#memory parameters
		self.current_len = int(self.encoder_input_shape[-1]/2)
		self.short_term_len = int (self.encoder_input_shape[-1]/4)
		self.long_term_len = int (self.encoder_input_shape[-1]/4)
		memory_h2c_shape = (self.output_dim,self.current_len)
		memory_h2s_shape = (self.output_dim,self.short_term_len)
		memory_h2l_shape = (self.output_dim,self.long_term_len) 
		print('memory configure:')
		print('current lenght:%d, short term length:%d, long term length:%d', %(current_len,short_term_len,long_term_len))
		self.W_m_h = InitUtil.init_weight_variable(memory_h2c_shape,init_method='glorot_uniform',name="W_m_h")
		self.W_m_s = InitUtil.init_weight_variable(memory_h2s_shape,init_method='glorot_uniform',name="W_m_s")
		self.W_m_l = InitUtil.init_weight_variable(memory_h2l_shape,init_method='glorot_uniform',name="W_m_l")

		self.memory_attention_size = 50
		self.m_a_h = InitUtil.init_weight_variable((self.output_dim,self.memory_attention_size),init_method='glorot_uniform',name="m_a_h")
		self.m_a_l = InitUtil.init_weight_variable((self.output_dim,self.memory_attention_size),init_method='glorot_uniform',name="m_a_l")
		self.m_a_b = InitUtil.init_weight_variable((self.memory_attention_size,),init_method='glorot_uniform',name="m_a_b")

		self.m_a = InitUtil.init_weight_variable((self.memory_attention_size,1),init_method='glorot_uniform',name="m_a")

		# decoder parameters
		self.T_w2v, self.T_mask = self.init_embedding_matrix()

		decoder_i2h_shape = (self.d_w2v,self.output_dim)
		decoder_h2h_shape = (self.output_dim,self.output_dim)
		self.W_d_r = InitUtil.init_weight_variable(decoder_i2h_shape,init_method='glorot_uniform',name="W_d_r")
		self.W_d_z = InitUtil.init_weight_variable(decoder_i2h_shape,init_method='glorot_uniform',name="W_d_z")
		self.W_d_h = InitUtil.init_weight_variable(decoder_i2h_shape,init_method='glorot_uniform',name="W_d_h")

		self.U_d_r = InitUtil.init_weight_variable(decoder_h2h_shape,init_method='orthogonal',name="U_d_r")
		self.U_d_z = InitUtil.init_weight_variable(decoder_h2h_shape,init_method='orthogonal',name="U_d_z")
		self.U_d_h = InitUtil.init_weight_variable(decoder_h2h_shape,init_method='orthogonal',name="U_d_h")

		self.b_d_r = InitUtil.init_bias_variable((self.output_dim,),name="b_d_r")
		self.b_d_z = InitUtil.init_bias_variable((self.output_dim,),name="b_d_z")
		self.b_d_h = InitUtil.init_bias_variable((self.output_dim,),name="b_d_h")


		
		self.W_a = InitUtil.init_weight_variable((self.encoder_input_shape[-1],self.attention_dim),init_method='glorot_uniform',name="W_a")
		self.U_a = InitUtil.init_weight_variable((self.output_dim,self.attention_dim),init_method='orthogonal',name="U_a")
		self.b_a = InitUtil.init_bias_variable((self.attention_dim,),name="b_a")

		self.W = InitUtil.init_weight_variable((self.attention_dim,1),init_method='glorot_uniform',name="W")

		self.A_z = InitUtil.init_weight_variable((self.encoder_input_shape[-1],self.output_dim),init_method='orthogonal',name="A_z")

		self.A_r = InitUtil.init_weight_variable((self.encoder_input_shape[-1],self.output_dim),init_method='orthogonal',name="A_r")

		self.A_h = InitUtil.init_weight_variable((self.encoder_input_shape[-1],self.output_dim),init_method='orthogonal',name="A_h")


		# classification parameters
		self.W_c = InitUtil.init_weight_variable((self.output_dim,self.voc_size),init_method='uniform',name='W_c')
		self.b_c = InitUtil.init_bias_variable((self.voc_size,),name="b_c")

	def init_embedding_matrix(self):
		'''init word embedding matrix
		'''
		voc_size = self.voc_size
		d_w2v = self.d_w2v	
		np_mask = np.vstack((np.zeros(d_w2v),np.ones((voc_size-1,d_w2v))))
		T_mask = tf.constant(np_mask, tf.float32, name='LUT_mask')

		LUT = np.zeros((voc_size, d_w2v), dtype='float32')
		for v in range(voc_size):
			LUT[v] = rng.randn(d_w2v)
			LUT[v] = LUT[v] / (np.linalg.norm(LUT[v]) + 1e-6)

		# word 0 is blanked out, word 1 is 'UNK'
		LUT[0] = np.zeros((d_w2v))
		# setup LUT!
		T_w2v = tf.Variable(LUT.astype('float32'),trainable=True)

		return T_w2v, T_mask 

	def init_visual_sequentail_memory(self):
		seqmem = tf.zeors_like(self.input_feature,dtype=tf.float32)
		seqmem = tf.tile(tf.reduce_sum(seqmem, axis=[1,2], keep_dims=True),[1,self.encoder_input_shape[1]+1,self.output_dim])

		return seqmem
	def encoder(self):
		'''
			visual feature part
		'''
		print('building encoder ... ...')
		def get_init_state(x, output_dims):
			initial_state = tf.zeros_like(x)
			initial_state = tf.reduce_sum(initial_state,axis=[1,2])
			initial_state = tf.expand_dims(initial_state,dim=-1)
			initial_state = tf.tile(initial_state,[1,self.output_dim])
			return initial_state

		
		
		timesteps = self.encoder_input_shape[1]

		embedded_feature = self.input_feature

		initial_state = get_init_state(embedded_feature, self.output_dim)


		axis = [1,0]+list(range(2,3))  # axis = [1,0,2]
		embedded_feature = tf.transpose(embedded_feature, perm=axis)

		input_feature = tf.TensorArray(
	            dtype=embedded_feature.dtype,
	            size=timesteps,
	            tensor_array_name='input_feature')
		if hasattr(input_feature, 'unstack'):
			input_feature = input_feature.unstack(embedded_feature)
		else:
			input_feature = input_feature.unpack(embedded_feature)	


		hidden_states = tf.TensorArray(
	            dtype=tf.float32,
	            size=timesteps,
	            tensor_array_name='hidden_states')


		def feature_step(time, hidden_states, h_tm1, visual_seq_mem):
			x_t = input_feature.read(time) # batch_size * dim

			preprocess_x_r = tf.nn.xw_plus_b(x_t, self.W_e_r, self.b_e_r)
			preprocess_x_z = tf.nn.xw_plus_b(x_t, self.W_e_z, self.b_e_z)
			preprocess_x_h = tf.nn.xw_plus_b(x_t, self.W_e_h, self.b_e_h)

			r = hard_sigmoid(preprocess_x_r+ tf.matmul(h_tm1, self.U_e_r))
			z = hard_sigmoid(preprocess_x_z+ tf.matmul(h_tm1, self.U_e_z))
			hh = tf.nn.tanh(preprocess_x_h+ tf.matmul(r*h_tm1, self.U_e_h))

			
			h = (1-z)*hh + z*h_tm1

			hidden_states = hidden_states.write(time, h)

			# long term memory 
			previous_memories = visual_seq_mem[:,0:time+1,:]
			mem_attd_ah = tf.expand_dims(tf.matmul(h,self.m_a_h),dim=1)

			mem_attd_al = tf.matmul(tf.reshape(previous_memories,[-1,self.output_dim]),self.m_a_l)
			mem_attd_al = tf.reshape(mem_attd_al,[-1,time+1,self.memory_attention_size])
			
			mem_attd_ab = tf.reshape(self.m_a_b,[1,1,self.memory_attention_size])

			temp_memory = tf.tanh(mem_attd_ah+mem_attd_al+mem_attd_ab)
			memory_alpha = tf.reshape(tf.matmul(tf.reshape(temp_memory,[-1,self.memory_attention_size]),self.m_a),[-1,time+1,1])
			memory_alpha = tf.nn.softmax(memory_alpha,dim=1)
			long_memory = tf.reduce_sum(tf.multiply(memory_alpha,previous_memories),axis=[1])
			long_memory = tf.matmul(long_memory,self.W_m_l) # [batch, ]
			# short term memory
			short_memory = tf.matmul(visual_seq_mem[:,time,:],self.W_m_s)

			# current memory
			current_memory = tf.matmul(h,self.W_m_h)

			m_i = tf.concat([current_memory,short_memory,long_memory],-1)

			pad_memory = tf.tile(tf.expand_dims(tf.zeros_like(m_i,dtype=tf.float32),dim=1),[1,self.encoder_input_shape[1]-time-1])
			visual_seq_mem = tf.concat([previous_memories,m_i,pad_memory],-1)
			return (time+1,hidden_states,h, visual_seq_mem)

		

		time = tf.constant(0, dtype='int32', name='time')
		visual_seq_mem = self.init_visual_sequentail_memory()

		feature_out = tf.while_loop(
	            cond=lambda time, *_: time < timesteps,
	            body=feature_step,
	            loop_vars=(time, hidden_states, initial_state, visual_seq_mem),
	            parallel_iterations=32,
	            swap_memory=True)

		last_output = feature_out[-2] 
		visual_seq_mem = feature_out[-1]
		return last_output, visual_seq_mem

	def decoder(self, initial_state):
		'''
			captions: (batch_size x timesteps) ,int32
			d_w2v: dimension of word 2 vector
		'''
		captions = self.input_captions

		print('building decoder ... ...')
		mask =  tf.not_equal(captions,0)


		loss_mask = tf.cast(mask,tf.float32)


		embedded_captions = tf.gather(self.T_w2v,captions)*tf.gather(self.T_mask,captions)

		timesteps = self.decoder_input_shape[1]


		# batch_size x timesteps x dim -> timesteps x batch_size x dim
		axis = [1,0]+list(range(2,3))  # axis = [1,0,2]
		embedded_captions = tf.transpose(embedded_captions, perm=axis) # permutate the input_x --> timestemp, batch_size, input_dims



		input_embedded_words = tf.TensorArray(
	            dtype=embedded_captions.dtype,
	            size=timesteps,
	            tensor_array_name='input_embedded_words')


		if hasattr(input_embedded_words, 'unstack'):
			input_embedded_words = input_embedded_words.unstack(embedded_captions)
		else:
			input_embedded_words = input_embedded_words.unpack(embedded_captions)	


		# preprocess mask
		mask = tf.expand_dims(mask,dim=-1)
		
		mask = tf.transpose(mask,perm=axis)

		input_mask = tf.TensorArray(
			dtype=mask.dtype,
			size=timesteps,
			tensor_array_name='input_mask'
			)

		if hasattr(input_mask, 'unstack'):
			input_mask = input_mask.unstack(mask)
		else:
			input_mask = input_mask.unpack(mask)


		train_hidden_state = tf.TensorArray(
	            dtype=tf.float32,
	            size=timesteps,
	            tensor_array_name='train_hidden_state')

		def step(x_t,h_tm1):

			ori_feature = tf.reshape(self.input_feature,(-1,self.encoder_input_shape[-1]))

			attend_wx = tf.reshape(tf.nn.xw_plus_b(ori_feature, self.W_a, self.b_a),(-1,self.encoder_input_shape[-2],self.attention_dim))
			attend_uh_tm1 = tf.tile(tf.expand_dims(tf.matmul(h_tm1, self.U_a),dim=1),[1,self.encoder_input_shape[-2],1])

			attend_e = tf.nn.tanh(attend_wx+attend_uh_tm1)
			attend_e = tf.matmul(tf.reshape(attend_e,(-1,self.attention_dim)),self.W)# batch_size * timestep
			# attend_e = tf.reshape(attend_e,(-1,attention_dim))
			attend_e = tf.nn.softmax(tf.reshape(attend_e,(-1,self.encoder_input_shape[-2],1)),dim=1)

			attend_fea = self.input_feature * tf.tile(attend_e,[1,1,self.encoder_input_shape[-1]])
			attend_fea = tf.reduce_sum(attend_fea,reduction_indices=1)

			preprocess_x_r = tf.nn.xw_plus_b(x_t, self.W_d_r, self.b_d_r)
			preprocess_x_z = tf.nn.xw_plus_b(x_t, self.W_d_z, self.b_d_z)
			preprocess_x_h = tf.nn.xw_plus_b(x_t, self.W_d_h, self.b_d_h)

			r = hard_sigmoid(preprocess_x_r+ tf.matmul(h_tm1, self.U_d_r) + tf.matmul(attend_fea,self.A_r))
			z = hard_sigmoid(preprocess_x_z+ tf.matmul(h_tm1, self.U_d_z) + tf.matmul(attend_fea,self.A_z))
			hh = tf.nn.tanh(preprocess_x_h+ tf.matmul(r*h_tm1, self.U_d_h) + tf.matmul(attend_fea,self.A_h))

			
			h = (1-z)*hh + z*h_tm1
			return h

		def train_step(time, train_hidden_state, h_tm1):
			x_t = input_embedded_words.read(time) # batch_size * dim
			mask_t = input_mask.read(time)

			h = step(x_t,h_tm1)

			tiled_mask_t = tf.tile(mask_t, tf.stack([1, h.get_shape().as_list()[1]]))

			h = tf.where(tiled_mask_t, h, h_tm1) # (batch_size, output_dims)
			
			train_hidden_state = train_hidden_state.write(time, h)

			return (time+1,train_hidden_state,h)

		

		time = tf.constant(0, dtype='int32', name='time')


		train_out = tf.while_loop(
	            cond=lambda time, *_: time < timesteps,
	            body=train_step,
	            loop_vars=(time, train_hidden_state, initial_state),
	            parallel_iterations=32,
	            swap_memory=True)


		train_hidden_state = train_out[1]
		train_last_output = train_out[-1] 
		
		if hasattr(train_hidden_state, 'stack'):
			train_outputs = train_hidden_state.stack()
		else:
			train_outputs = train_hidden_state.pack()

		axis = [1,0] + list(range(2,3))
		train_outputs = tf.transpose(train_outputs,perm=axis)



		train_outputs = tf.reshape(train_outputs,(-1,self.output_dim))
		train_outputs = tf.nn.dropout(train_outputs, self.dropout)
		predict_score = tf.matmul(train_outputs,self.W_c) + tf.reshape(self.b_c,(1,self.voc_size))
		predict_score = tf.reshape(predict_score,(-1,timesteps,self.voc_size))
		# predict_score = tf.nn.softmax(predict_score,-1)
		# test phase


		test_input_embedded_words = tf.TensorArray(
	            dtype=embedded_captions.dtype,
	            size=timesteps+1,
	            tensor_array_name='test_input_embedded_words')

		predict_words = tf.TensorArray(
	            dtype=tf.int64,
	            size=timesteps,
	            tensor_array_name='predict_words')

		test_hidden_state = tf.TensorArray(
	            dtype=tf.float32,
	            size=timesteps,
	            tensor_array_name='test_hidden_state')
		test_input_embedded_words = test_input_embedded_words.write(0,embedded_captions[0])

		def test_step(time, test_hidden_state, test_input_embedded_words, predict_words, h_tm1):
			x_t = test_input_embedded_words.read(time) # batch_size * dim

			h = step(x_t,h_tm1)

			test_hidden_state = test_hidden_state.write(time, h)


			# drop_h = tf.nn.dropout(h, 0.5)
			drop_h = h*self.dropout
			predict_score_t = tf.matmul(drop_h,self.W_c) + tf.reshape(self.b_c,(1,self.voc_size))

			# predict_score_t = tf.matmul(normed_h,tf.transpose(T_w2v,perm=[1,0]))
			predict_score_t = tf.nn.softmax(predict_score_t,dim=-1)
			predict_word_t = tf.argmax(predict_score_t,-1)

			predict_words = predict_words.write(time, predict_word_t) # output


			predict_word_t = tf.gather(self.T_w2v,predict_word_t)*tf.gather(self.T_mask,predict_word_t)

			test_input_embedded_words = test_input_embedded_words.write(time+1,predict_word_t)

			return (time+1,test_hidden_state, test_input_embedded_words, predict_words, h)


		time = tf.constant(0, dtype='int32', name='time')


		test_out = tf.while_loop(
	            cond=lambda time, *_: time < timesteps,
	            body=test_step,
	            loop_vars=(time, test_hidden_state, test_input_embedded_words, predict_words, initial_state),
	            parallel_iterations=32,
	            swap_memory=True)


		predict_words = test_out[-2]
		
		if hasattr(predict_words, 'stack'):
			predict_words = predict_words.stack()
		else:
			predict_words = predict_words.pack()

		axis = [1,0] + list(range(2,3))

		predict_words = tf.transpose(predict_words,perm=[1,0])
		predict_words = tf.reshape(predict_words,(-1,timesteps))

		return predict_score, predict_words, loss_mask

	def build_model(self):
		print('building model ... ...')
		self.init_parameters()
		last_output, visual_seq_mem = self.encoder()
		predict_score, predict_words, loss_mask = self.decoder(visual_seq_mem[:,-1,:])
		return predict_score, predict_words





