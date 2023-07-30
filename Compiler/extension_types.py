# from Compiler.types import *
#
#
# class TableEntry:
#     def __init__(self, col, header=None):
#         self.val = sint.Array(col)
#         self.header_map = {}
#
#     def set_header(self, header):
#         for i, key in enumerate(header):
#             self.header_map[key] = i
#
#
# class Table:
#     def __init__(self, row, col, header=None):
#         self.header_map = {}
#
#     def set_header(self, header):
#         for i, key in enumerate(header):
#             self.header_map[key] = i
#
#     def input_from(self, pid):
