# from tensor import get_opid, Tensor, get_prepare, Operation, tensors, gradient_operation, op_id_store,fake_propagate, set_opid,dl_d
from tensor import *
from glob import glob
import math
import re
import numpy as np
# from turtle import forward, shape
from itertools import zip_longest
from Compiler import mpc_math, util
from Compiler.types import *
from Compiler.types import _unreduced_squant
from Compiler.library import *
from Compiler.util import is_zero, tree_reduce
from Compiler.comparison import CarryOutRawLE
# from Compiler.GC.types import sbitintis_train
from functools import reduce
from typing import List, NamedTuple, Callable, Dict, Optional, Union, Tuple, Any
approx = False
def relu(input, inplace=False):  # todo
    op_id = get_opid()
    @buildingblock(get_program().globalbuildingblock)
    def propagate(dl_doutputs, operation):
        dl_dy, = dl_doutputs
        input_ = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        if input_.req_grad:
            dl_d[input_.name]+=(input_.value[:]>=0)*dl_dy[:]
            
    prepare = get_prepare()
    if prepare:
        assert isinstance(input, Tensor),"Invalid Input"
        if isinstance(input.value,Array):
            new_value=Array(input.shape[0],input.value.value_type)
        else:
            new_value=MultiArray(list(input.shape) ,input.value.value_type)
        output = Tensor(new_value, req_grad=input.req_grad)
        if input.req_grad:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=propagate)
        else:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=fake_propagate)
        gradient_operation.append(operation)
        operation_id = len(gradient_operation) - 1
        op_id_store[op_id] = operation_id
        set_opid(op_id+1)
    else:
        operation = gradient_operation[op_id_store[op_id]]
        input = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        output.value[:] = (0 < input.value[:]).if_else(input.value[:], 0) 
        set_opid(op_id+1)  # record the input and output of the op
    return output

@vectorize
def approx_sigmoid(x, n=3):
    """ Piece-wise approximate sigmoid as in
    `Hong et al. <https://arxiv.org/abs/2002.04344>`_

    :param x: input
    :param n: number of pieces, 3 (default) or 5
    """
    if n == 5:
        cuts = [-5, -2.5, 2.5, 5]
        le = [0] + [x <= cut for cut in cuts] + [1]
        select = [le[i + 1] - le[i] for i in range(5)]
        outputs = [cfix(10 ** -4),
                   0.02776 * x + 0.145,
                     * x + 0.5,
                   0.02776 * x + 0.85498,
                   cfix(1 - 10 ** -4)]
        return sum(a * b for a, b in zip(select, outputs))
    else:
        a = x < -0.5
        b = x > 0.5
        return a.if_else(0, b.if_else(1, 0.5 + x))

def gelu(input):  # todo low priority
    pass

def log_e(x):
    return mpc_math.log_fx(x, math.e)

use_mux = False
def exp(x):
    if use_mux:
        return mpc_math.mux_exp(math.e, x)
    else:
        return mpc_math.pow_fx(math.e, x)

def get_limit(x):
    exp_limit = 2 ** (x.k - x.f - 1)
    return math.log(exp_limit)

def sanitize(x, raw, lower, upper):
    limit = get_limit(x)
    res = (x > limit).if_else(upper, raw)
    return (x < -limit).if_else(lower, res)

def sigmoid_from_e_x(x,e_x):
    return sanitize(x, 1 / (1 + e_x), 0, 1)

def sigmoid(input): #todo
    op_id = get_opid()
    @buildingblock(get_program().globalbuildingblock)
    def propagate(dl_doutputs, operation):
        dl_dy, = dl_doutputs
        input_ = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        # if input_.req_grad:
        dl_d[input_.name]+=output.value[:]*(1-output.value[:])*dl_dy[:]
            
    prepare = get_prepare()
    if prepare:
        assert isinstance(input, Tensor),"Invalid Input"
        if isinstance(input.value,Array):
            new_value=Array(input.shape[0],input.value.value_type)
        else:
            new_value=MultiArray(list(input.shape) ,input.value.value_type)
        output = Tensor(new_value, req_grad=input.req_grad)
        if input.req_grad:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=propagate)
        else:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=fake_propagate)
        gradient_operation.append(operation)
        operation_id = len(gradient_operation) - 1
        op_id_store[op_id] = operation_id
        set_opid(op_id+1)
    else:
        operation = gradient_operation[op_id_store[op_id]]
        input = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        if approx:
            output.value[:]=approx_sigmoid(input.value[:])
        else:
            output.value[:] =  sigmoid_from_e_x(input.value[:],exp(-input.value[:]))
        set_opid(op_id+1)  # record the input and output of the op
    return output


def logsigmoid(input):  # todo
    op_id = get_opid()
    @buildingblock(get_program().globalbuildingblock)
    def propagate(dl_doutputs, operation):
        dl_dy, = dl_doutputs
        input_ = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        if input_.req_grad:
            dl_d[input_.name]+=1/(1+exp(output.value[:]))*dl_dy[:]
            
    prepare = get_prepare()
    if prepare:
        assert isinstance(input, Tensor),"Invalid Input"
        if isinstance(input.value,Array):
            new_value=Array(input.shape[0],input.value.value_type)
        else:
            new_value=MultiArray(list(input.shape) ,input.value.value_type)
        output = Tensor(new_value, req_grad=input.req_grad)
        if input.req_grad:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=propagate)
        else:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=fake_propagate)
        gradient_operation.append(operation)
        operation_id = len(gradient_operation) - 1
        op_id_store[op_id] = operation_id
        set_opid(op_id+1)
    else:
        operation = gradient_operation[op_id_store[op_id]]
        input = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        output.value[:] = -log_e(1+exp(-input.value[:]))
        set_opid(op_id+1)  # record the input and output of the op
    return output


def tanh(input):  # todo
    op_id = get_opid()
    @buildingblock(get_program().globalbuildingblock)
    def propagate(dl_doutputs, operation):
        dl_dy, = dl_doutputs
        input_ = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        if input_.req_grad:
            dl_d[input_.name]+=(1-output.value[:]*output.value[:])*dl_dy[:]
            
    prepare = get_prepare()
    if prepare:
        assert isinstance(input, Tensor),"Invalid Input"
        if isinstance(input.value,Array):
            new_value=Array(input.shape[0],input.value.value_type)
        else:
            new_value=MultiArray(list(input.shape) ,input.value.value_type)
        output = Tensor(new_value, req_grad=input.req_grad)
        if input.req_grad:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=propagate)
        else:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=fake_propagate)
        gradient_operation.append(operation)
        operation_id = len(gradient_operation) - 1
        op_id_store[op_id] = operation_id
        set_opid(op_id+1)
    else:
        operation = gradient_operation[op_id_store[op_id]]
        input = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        x=input.value[:]
        ex=exp(x)
        e_x=exp(-x)
        output.value[:] = sanitize(x, (ex-e_x)/(ex+e_x), -1, 1)    
        set_opid(op_id+1)  # record the input and output of the op
    return output
    


def softmax(input, dim=None):  # todo
    pass


def log_softmax(input, dim=None):  # todo
    pass


def linear(input, weight, bias=None):
    assert isinstance(input,Tensor) and isinstance(weight,Tensor),"Invalid input or weight"
    assert input.shape[-1]==weight.shape[-1],"Invalid Dimension"
    weight.value=weight.value.transpose()
    output=input.mm(weight)
    if bias is None:
        pass
    else:
        output.value[:]=(bias+output)
    return output
def new_squant():
        class _(sfix):
            params = None
        return _


def conv2d(input:Tensor, weight:Tensor, bias=None, stride=[1,1], padding=[0,0]):
    #input.shape:(batch_size,channel_in,H,W)
    #weight.shape:(out_channels, in_channels // groups, H,W)
    #bais:(out_channels)
    op_id = get_opid()
    @buildingblock(get_program().globalbuildingblock)
    def propagate(dl_doutputs, operation):
        dl_dy, = dl_doutputs
        input = tensors[operation.inputs[0]]
        weight= tensors[operation.inputs[1]]
        output = tensors[operation.outputs[0]]
        _, _,weights_h, weights_w= weight.shape
        _,  n_channels_in,inputs_h, inputs_w = input.shape
        _,  n_channels_out,output_h, output_w = output.shape

        stride_h, stride_w = stride
        padding_h, padding_w = padding
        
        input_size = input.shape[2] * input.shape[3] * input.shape[0] #why have no channel_in? 128*36
        # batch_repeat = regint.Matrix(input.shape[0], input.shape[2] * input.shape[3]) # 128,6*6
        # batch_repeat.assign_vector(batch.get(
        #     regint.inc(input_size, 0, 1, 1, input.shape[0])) *reduce(operator.mul, input.shape[1:])) 
        #存储到batch_repeat
        @for_range_opt_multithread(self.n_threads, [n_channels_in, n_channels_out])
        def _(i, j):
            inputs = input.value.get_part_vector(i,).pre_mul()
            
            b = regint.inc(N * output_w * output_h, self.nabla_Y.address + j, n_channels_out, N)
            rep_out = regint.inc(output_h * output_w * N, 0, 1, 1, N) * \
                reduce(operator.mul, self.output_shape[1:])
            nabla_outputs = output.value.get_part_vector(j).pre_mul()
            res = sint(size = weights_h * weights_w)
            conv2ds(res, inputs, nabla_outputs, weights_h, weights_w, inputs_h,
                    inputs_w, output_h, output_w, -stride_h, -stride_w, N,
                    padding_h, padding_w, 1)
            reduced = unreduced_sfix._new(res).reduce_after_mul()
            self.nabla_weights.assign_vector_by_indices(reduced, j, None, None, i)
        
        
    prepare = get_prepare()
    if prepare:
        assert isinstance(input, Tensor) and isinstance(weight, Tensor) ,"Invalid Input and weight"
        assert len(input.shape)==4 and len(weight.shape)==4,"Invalid Dimension input and weight"
        out_shape=[input.shape[0],weight.shape[0],(input.shape[2]+2*padding[0]-weight.shape[2])//stride[0]+1,
                   (input.shape[3]+2*padding[1]-weight.shape[3])//stride[1]+1] #out_shape.size:[Batch_size,out_channel,H_out,W_out]
        new_value=MultiArray(out_shape,input.value.value_type)
        output = Tensor(new_value, req_grad=input.req_grad)
        if input.req_grad:
            operation = Operation(inputs=[input.name,weight.name], outputs=[output.name], propagate=propagate)
        else:
            operation = Operation(inputs=[input.name,weight.name], outputs=[output.name], propagate=fake_propagate)
        gradient_operation.append(operation)
        operation_id = len(gradient_operation) - 1
        op_id_store[op_id] = operation_id
        set_opid(op_id+1)
    else:
        operation = gradient_operation[op_id_store[op_id]]
        input_ = tensors[operation.inputs[0]]
        weight_= tensors[operation.inputs[1]]
        output = tensors[operation.outputs[0]] 
        n_threads=8 if input_.numel() > 2**20 else 1
        n_parts = max(1, round((n_threads or 1) / weight_.shape[0]))
        while input_.shape[0] % n_parts != 0:
            n_parts -= 1
        print('Convolution in %d parts' % n_parts)
        part_size = input_.shape[0] // n_parts
        unreduced = MultiArray(output.shape, sint, address=output.value.address)
        size_=part_size*reduce(operator.mul,input_.shape[1:])
        @for_range_multithread(n_threads,1,[n_parts,weight_.shape[0]])
        def _(i, j):
            inputs=input_.value.get_vector(i*size_,size_).v
            # print(len(inputs))
            weights = weight_.value.get_part_vector(j).v
            res = sint(size = output.shape[2] * output.shape[3] * part_size)
            conv2ds(res, inputs, weights, output.shape[2],output.shape[3],
                        input_.shape[2], input_.shape[3], weight_.shape[2], weight_.shape[3],
                        stride[0], stride[1], input_.shape[1], padding[0], padding[1],
                        part_size)
            if bias:
                res += bias.expand_to_vector(j, res.size).v
            addresses=regint.inc(res.size, unreduced[i * part_size].address + j,weight_.shape[0])
            res.store_in_mem(addresses)
        # n_summands=weight_.shape[2]*weight_.shape[3]*input_.shape[1] #weights_h * weights_w * n_channels_in
        n_outputs = input_.shape[0] * reduce(operator.mul, output.shape[1:])
        @multithread(n_threads, n_outputs,
                     1000 if sfix.round_nearest else 10 ** 6)                                                                                
        def _(base, n_per_thread):
            res = sfix().unreduced(sint.load_mem(unreduced.address + base,
                              size=n_per_thread),sfix).reduce_after_mul()
            res.store_in_mem(output.value.address + base)
        set_opid(op_id+1)  # record the input and output of the op
    return output


def conv_transpose2d(input, weight, bias=None, stride=1, padding=0, outputpadding=0):
     pass


def max_pool2d(input, kernel_size, stride=None, padding=0,):
    pass


def avg_pool2d(input, kernel_size, stride=None, padding=0,):
    pass


def dropout(input, p=0.5, training=False, inplace=False):  # todo
    op_id = get_opid()
    @buildingblock(get_program().globalbuildingblock)
    def propagate(dl_doutputs, operation):
        dl_dx, = dl_doutputs
        bin_value, = operation.intermediate
        dl_dself = dl_d[operation.inputs[0]]
        
        dl_dself[:] += 1 / (1 - p) * bin_value[:] * dl_dx[:]
            
    prepare = get_prepare()
    if prepare:
        assert isinstance(input, Tensor), "Invalid Input"
        if isinstance(input.value,Array):
            new_value = Array(input.size, input.value.value_type)
            bin_value = Array(input.size, input.value.value_type)
        else:
            new_value = MultiArray(input.sizes, input.value.value_type)
            bin_value = MultiArray(input.sizes, input.value.value_type)
        output = Tensor(new_value, req_grad=input.req_grad)
        if input.req_grad:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=propagate, intermediate=[bin_value])
        else:
            operation = Operation(inputs=[input.name], outputs=[output.name], propagate=fake_propagate, intermediate=[bin_value])
        gradient_operation.append(operation)
        operation_id = len(gradient_operation) - 1
        op_id_store[op_id] = operation_id
        set_opid(op_id+1)
    else:
        operation = gradient_operation[op_id_store[op_id]]
        input = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        bin_value, = operation.intermediate
        if training:
            n_bits = -math.log(p, 2)
            assert n_bits == int(n_bits)
            n_bits = int(n_bits)
            
            B = util.tree_reduce(util.or_op, 
                    (sint.get_random_bit(size=input.value.total_size())
                        for i in range(n_bits)))
            bin_value.assign_vector(B)
            
            output.value.assign_vector(1 / (1 - p) *
                input.value.get_vector() * B.get_vector())
        else:
            output.value[:] = input.value[:]
        set_opid(op_id+1)  # record the input and output of the op
    return output


def one_hot(input, num_classes=-1):
    # i think user should specify the num_classes, if not, we should calculate the max value in input.
    """example:
    one_hot(torch.tensor([0, 1, 2, 3, 4]), num_classes=8)
    tensor([[1, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0, 0]])"""
    assert isinstance(input, Tensor), "input should be Tensor"
    assert input.value.value_type == cint, "input should be cint"
    x = input.value
    in_sizes = x.sizes
    b = reduce(operator.mul, in_sizes) if len(in_sizes) >= 2 else in_sizes[0]
    output = MultiArray([*in_sizes, num_classes], x.value_type)

    output.view(-1, num_classes)

    for i in range(b):
        output[i][x.get_vector()[i]] = 1

    output.view(*in_sizes, num_classes)
    return Tensor(output)


def normalize(input, p=2.0, dim=1, eps=1e-12, out=None):  # todo
    pass


def batch_norm(input, weight=None, bias=None, training=False, eps=1e-05):
    
    assert isinstance(input,Tensor) ,"Invalid input"
    
    x_mean = input.mean(dim=[0,2,3])
    x_std = input.std(dim=[0,2,3])
    x_hat = (input -x_mean) / (x_std) 
    
    return x_hat * weight + bias



def layer_norm(input, normalized_shape, weight=None, bias=None, eps=1e-05):
    pass


def cosine_similarity(x1, x2, dim=1, eps=1e-8):
    pass


def pdist(input, p=2):  # todo
    pass


def kl_div(input, target, log_target=False):
    pass


def l1_loss(input, target):
    pass


def nll_loss(input, target, weight=None):
    pass


def mse_loss(input, target): # todo
    pass


def binary_cross_entropy(input, target, weight=None):
    pass


def cross_entropy(input, target, weight=None):
    pass
