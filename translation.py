# coding=utf-8
"""
翻译动作：
提前遍历翻译：
if -> IF LPAREN condition RPAREN LBRACE statements RBRACE
   | IF LPAREN condition RPAREN LBRACE statements RBRACE ELSE LBRACE statements RBRACE
   | IF LPAREN condition RPAREN LBRACE statements RBRACE ELIF LPAREN condition RPAREN LBRACE statements RBRACE ELSE LBRACE statements RBRACE
while -> WHILE LPAREN condition RPAREN LBRACE statements RBRACE
for -> FOR LPAREN assignment SEMICOLON condition SEMICOLON selfvar RPAREN LBRACE statements RBRACE
break -> BREAK
遍历时翻译：
assignment -> leftval ASSIGN expr | leftval ASSIGN array { value = expr.value; set_value(var_table, leftval.id, value); }
leftval -> leftval1 LLIST expr RLIST  { leftval.id = (leftval1.id, expr.value);
                                        leftval.value = get_value(var_table, leftval.id); }
leftval -> ID  { leftval.id = (ID.id, None);
                 if (ID.value != NIL) { set_value(var_table, leftval.id, ID.value); } }
leftval -> leftval1 LLIST expr RLIST  { leftval.id = (leftval1.id, expr.value); }
expr -> expr1 '+' term  { expr.value = expr1.value + term.value; }
expr -> expr1 '-' term  { expr.value = expr1.value - term.value; }
expr -> term  { expr.value = term.value; }
term -> term1 '*' factor  { term.value = term1.value * factor.value; }
term -> term1 '/' factor  { term.value = term1.value / factor.value; }
term -> term1 '//' factor  { term.value = term1.value // factor.value; }
term -> factor { term.value = factor.value; }
factor -> leftval  { value = get_value(var_table, leftval.id); factor.value = value; }
factor -> NUMBER  { factor.value = NUMBER.value; }
factor -> len  { factor.value = len.value; }
factor -> '(' expr ')'  { fact.value = expr.value; }
exprs -> exprs1 ',' expr  { exprs.value = exprs1.value + [expr.value]; }
exprs -> expr  { exprs.value = [expr.value]; }
print -> PRINT '(' exprs ')'  { print(*exprs.value); }
print -> PRINT '(' ')'  { print(); }
len -> LEN '(' leftval ')'  { len.value = len(get_value(var_table, leftval.id)) }
array -> '[' exprs ']'  { array.value = exprs.value; }
array -> '[' ']' { array.value = []; }
selfvar -> leftval '++'  { value = get_value(var_table, self._tree.child(0).id);
                           value = value + 1;
                           set_value(var_table, leftval.id, value); }
selfvar -> leftval '--'  { value = get_value(var_table, self._tree.child(0).id);
                           value = value - 1;
                           set_value(var_table, leftval.id, value); }
condition -> condition OR join  { condition.value = condition1.value or join.value; }
condition -> join  { condition.value = join.value; }
join -> join AND equality | equality  { join.value = join1.value or equality.value; }
join -> equality  { join.value = equality.value; }
equality -> equality '==' rel  { equality.value = equality1.value == rel.value; }
equality -> equality '!=' rel  { equality.value = equality1.value != rel.value; }
rel -> expr '<' expr1  { rel.value = exp.value < expr1.value; }
rel -> expr '<=' expr1  { rel.value = exp.value <= expr1.value; }
rel -> expr '>' expr1  { rel.value = exp.value > expr1.value; }
rel -> expr '>=' expr1  { rel.value = exp.value >= expr1.value; }
rel -> expr  { rel.value = bool(exp.value); }
"""
from node import *

DEBUG_MODE = True  # 调试时输出部分运行信息


class Translator:

    @staticmethod
    def get_value(tb, vid):
        name, sub = vid
        if not isinstance(name, tuple):
            if sub is None:
                return tb[name]
            return tb.get[name][sub]
        if sub is None:
            return Translator.get_value(tb, name)
        return Translator.get_value(tb, name)[sub]

    @staticmethod
    def set_value(tb, vid, val):
        name, sub = vid
        if not isinstance(name, tuple):
            if sub is None:
                tb[name] = val
                return
            tb[name][sub] = val
            return
        if sub is None:
            Translator.set_value(tb, name, val)
            return
        Translator.get_value(tb, name)[sub] = val

    def __init__(self, tree, tb=None, loop=0, break_flag=False):
        self._tree = tree
        self.var_table = {}  # variable table
        self._old_table = {}
        if tb is not None:
            self._old_table = tb
            self.var_table.update(tb)
        self.loop_flag = loop  # 循环内指示器，大于0为循环层数，等于0为不在循环内，小于0非法
        self.break_flag = break_flag  # break指示器

    def _save(self, tran):
        self.var_table = tran.var_table
        self.loop_flag = tran.loop_flag
        self.break_flag = tran.break_flag

    def translate(self):
        if self.break_flag:
            return
        # 提前翻译 if for while
        if isinstance(self._tree, NonTerminal):
            # If
            if self._tree.type == 'If':
                """if : IF LPAREN condition RPAREN LBRACE statements RBRACE"""
                assert len(self._tree.children) in (7, 11, 18), 'Syntax error'
                assert isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'if' and \
                       isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '(' and \
                       isinstance(self._tree.child(2), NonTerminal) and self._tree.child(2).type == 'Condition' and \
                       isinstance(self._tree.child(3), Terminal) and self._tree.child(3).text == ')' and \
                       isinstance(self._tree.child(4), Terminal) and self._tree.child(4).text == '{' and \
                       isinstance(self._tree.child(5), NonTerminal) and self._tree.child(5).type == 'Statements' and \
                       isinstance(self._tree.child(6), Terminal) and self._tree.child(6).text == '}', 'Syntax error'
                if DEBUG_MODE: print('if (...)')
                tran = Translator(self._tree.child(2), tb=self.var_table,
                                  loop=self.loop_flag, break_flag=self.break_flag)  # Condition
                tran.translate()
                self._save(tran)
                condition = self._tree.child(2).value
                if condition:
                    if DEBUG_MODE: print('then {...}  # if-then')
                    tran = Translator(self._tree.child(5), tb=self.var_table,
                                      loop=self.loop_flag, break_flag=self.break_flag)  # Statements
                    tran.translate()
                    self._save(tran)
                if len(self._tree.children) == 11:
                    """ELSE LBRACE statements2 RBRACE"""
                    assert isinstance(self._tree.child(7), Terminal) and self._tree.child(7).text == 'else' and \
                           isinstance(self._tree.child(8), Terminal) and self._tree.child(8).text == '{' and \
                           isinstance(self._tree.child(9), NonTerminal) and self._tree.child(9).type == 'Statements' and \
                           isinstance(self._tree.child(10), Terminal) and \
                           self._tree.child(10).text == '}', 'Syntax error'
                    if not condition:  # 只有if没有成立才执行
                        if DEBUG_MODE: print('else {...}  # else-else')
                        tran = Translator(self._tree.child(9), tb=self.var_table,
                                          loop=self.loop_flag, break_flag=self.break_flag)  # Statements2
                        tran.translate()
                        self._save(tran)
                elif len(self._tree.children) == 18:
                    """ELIF LPAREN condition2 RPAREN LBRACE statements2 RBRACE ELSE LBRACE statements3 RBRACE"""
                    assert isinstance(self._tree.child(7), Terminal) and self._tree.child(7).text == 'elif' and \
                           isinstance(self._tree.child(8), Terminal) and self._tree.child(8).text == '(' and \
                           isinstance(self._tree.child(9), NonTerminal) and self._tree.child(9).type == 'Condition' and \
                           isinstance(self._tree.child(10), Terminal) and self._tree.child(10).text == ')' and \
                           isinstance(self._tree.child(11), Terminal) and self._tree.child(11).text == '{' and \
                           isinstance(self._tree.child(12), NonTerminal) and self._tree.child(
                        12).type == 'Statements' and \
                           isinstance(self._tree.child(13), Terminal) and self._tree.child(13).text == '}' and \
                           isinstance(self._tree.child(14), Terminal) and self._tree.child(14).text == 'else' and \
                           isinstance(self._tree.child(15), Terminal) and self._tree.child(15).text == '{' and \
                           isinstance(self._tree.child(16), NonTerminal) and self._tree.child(
                        16).type == 'Statements' and \
                           isinstance(self._tree.child(17), Terminal) and self._tree.child(
                        17).text == '}', 'Syntax error'
                    if not condition:  # 只有if没有成立才执行
                        if DEBUG_MODE: print('elif (...)')
                        tran = Translator(self._tree.child(9), tb=self.var_table,
                                          loop=self.loop_flag, break_flag=self.break_flag)  # Condition2
                        tran.translate()
                        self._save(tran)
                        elif_condition = self._tree.child(9).value
                        if elif_condition:
                            if DEBUG_MODE: print('then {...}  # elif-then')
                            tran = Translator(self._tree.child(12), tb=self.var_table,
                                              loop=self.loop_flag, break_flag=self.break_flag)  # Statements2
                            tran.translate()
                            self._save(tran)
                        else:  # 只有if没有成立才执行
                            if DEBUG_MODE: print('else {...}  # elif-else')
                            tran = Translator(self._tree.child(16), tb=self.var_table,
                                              loop=self.loop_flag, break_flag=self.break_flag)  # Statements3
                            tran.translate()
                            self._save(tran)
                return
            # While
            elif self._tree.type == 'While':
                """while : WHILE LPAREN condition RPAREN LBRACE statements RBRACE"""
                assert len(self._tree.children) == 7 and \
                       isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'while' and \
                       isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '(' and \
                       isinstance(self._tree.child(2), NonTerminal) and self._tree.child(2).type == 'Condition' and \
                       isinstance(self._tree.child(3), Terminal) and self._tree.child(3).text == ')' and \
                       isinstance(self._tree.child(4), Terminal) and self._tree.child(4).text == '{' and \
                       isinstance(self._tree.child(5), NonTerminal) and self._tree.child(5).type == 'Statements' and \
                       isinstance(self._tree.child(6), Terminal) and self._tree.child(6).text == '}', 'Syntax error'
                if DEBUG_MODE: print('while (...)')
                _loop_count = 0
                self.loop_flag += 1  # 进入一层循环
                while True:
                    tran = Translator(self._tree.child(2), tb=self.var_table,
                                      loop=self.loop_flag, break_flag=self.break_flag)  # Condition
                    tran.translate()
                    self._save(tran)
                    condition = self._tree.child(2).value
                    if not condition:
                        if DEBUG_MODE: print('# end-while')
                        self.loop_flag -= 1  # 跳出一层循环
                        break
                    if DEBUG_MODE:
                        print('do {...}  # while, count =', (_loop_count := _loop_count + 1),
                              'indent =', self.loop_flag)
                    tran = Translator(self._tree.child(5), tb=self.var_table,
                                      loop=self.loop_flag, break_flag=self.break_flag)  # Statements
                    tran.translate()
                    self._save(tran)
                    if self.break_flag:
                        self.break_flag = False  # 执行break
                        self.loop_flag -= 1  # 跳出一层循环
                        break
                return
            # For
            elif self._tree.type == 'For':
                """for : FOR LPAREN assignment SEMICOLON condition SEMICOLON selfvar RPAREN LBRACE statements RBRACE"""
                assert len(self._tree.children) == 11 and \
                       isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'for' and \
                       isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '(' and \
                       isinstance(self._tree.child(2), NonTerminal) and self._tree.child(2).type == 'Assignment' and \
                       isinstance(self._tree.child(3), Terminal) and self._tree.child(3).text == ';' and \
                       isinstance(self._tree.child(4), NonTerminal) and self._tree.child(4).type == 'Condition' and \
                       isinstance(self._tree.child(5), Terminal) and self._tree.child(5).text == ';' and \
                       isinstance(self._tree.child(6), NonTerminal) and self._tree.child(6).type == 'SelfVar' and \
                       isinstance(self._tree.child(7), Terminal) and self._tree.child(7).text == ')' and \
                       isinstance(self._tree.child(8), Terminal) and self._tree.child(8).text == '{' and \
                       isinstance(self._tree.child(9), NonTerminal) and self._tree.child(9).type == 'Statements' and \
                       isinstance(self._tree.child(10), Terminal) and self._tree.child(10).text == '}', 'Syntax error'
                if DEBUG_MODE: print('for (...;...;...)')
                _loop_count = 0
                tran = Translator(self._tree.child(2), tb=self.var_table,
                                  loop=self.loop_flag, break_flag=self.break_flag)  # Assignment
                tran.translate()
                self._save(tran)
                self.loop_flag += 1  # 进入一层循环
                while True:
                    tran = Translator(self._tree.child(4), tb=self.var_table,
                                      loop=self.loop_flag, break_flag=self.break_flag)  # Condition
                    tran.translate()
                    self._save(tran)
                    condition = self._tree.child(4).value
                    if not condition:
                        if DEBUG_MODE: print('# end-for')
                        self.loop_flag -= 1  # 跳出一层循环
                        break
                    if DEBUG_MODE:
                        print('do {...}  # for, count =', (_loop_count := _loop_count + 1),
                              'indent =', self.loop_flag)
                    tran = Translator(self._tree.child(9), tb=self.var_table,
                                      loop=self.loop_flag, break_flag=self.break_flag)  # Statements
                    tran.translate()
                    self._save(tran)
                    if self.break_flag:
                        self.break_flag = False  # 执行break
                        self.loop_flag -= 1  # 跳出一层循环
                        break
                    tran = Translator(self._tree.child(6), tb=self.var_table,
                                      loop=self.loop_flag, break_flag=self.break_flag)  # SelfVar
                    tran.translate()
                    self._save(tran)
                return
            # Break
            elif self._tree.type == 'Break':
                assert len(self._tree.children) == 1 and \
                       isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'break', 'Syntax error'
                assert self.loop_flag > 0, 'Syntax error: use "break" in non-loop statements'
                self.break_flag = True  # 转为break状态
                if DEBUG_MODE: print('BREAK!')
                return

        # 深度优先遍历语法树
        for child in self._tree.children:
            tran = Translator(child, tb=self.var_table,
                              loop=self.loop_flag, break_flag=self.break_flag)
            tran.translate()
            self._save(tran)

        # Translation
        if isinstance(self._tree, NonTerminal):
            # Assignment
            if self._tree.type == 'Assignment':
                '''assignment -> leftval ASSIGN expr'''
                assert len(self._tree.children) == 3, 'Syntax error'
                assert isinstance(self._tree.child(0), LeftValue) and \
                       isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '=' and \
                       isinstance(self._tree.child(2), NonTerminal) and \
                       self._tree.child(2).type in ('Expr', 'Array'), 'Syntax error'
                value = self._tree.child(2).value
                self.set_value(self.var_table, self._tree.child(0).id, value)  # update var_table
                if DEBUG_MODE: print('assignment', self._tree.child(0).id, value)
            # LeftVal
            elif self._tree.type == 'LeftVal':
                """leftval -> leftval1 LLIST expr RLIST | ID"""
                assert len(self._tree.children) == 1 or len(self._tree.children) == 4, 'Syntax error'
                if len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), ID), 'Syntax error'
                    self._tree.id = (self._tree.child(0).id, None)
                    if self._tree.child(0).value is not NIL:
                        self.set_value(self.var_table, self._tree.id, self._tree.child(0).value)
                        if DEBUG_MODE: print('assignment', self._tree.id, self._tree.child(0).value)
                elif len(self._tree.children) == 4:
                    assert isinstance(self._tree.child(0), LeftValue) and \
                           isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '[' and \
                           isinstance(self._tree.child(2), NonTerminal) and self._tree.child(2).type == 'Expr' and \
                           isinstance(self._tree.child(3), Terminal) and self._tree.child(3).text == ']', 'Syntax error'
                    self._tree.id = (self._tree.child(0).id, self._tree.child(2).value)
            # Expr
            elif self._tree.type == 'Expr':
                '''expr : expr '+' term | expr '-' term | term'''
                assert len(self._tree.children) == 1 or len(self._tree.children) == 3, 'Syntax error'
                if len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Term', 'Syntax error'
                    self._tree.value = self._tree.child(0).value
                elif len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and self._tree.child(0).type == 'Expr' and \
                           isinstance(self._tree.child(1), Terminal) and (self._tree.child(1).text in ('+', '-')) and \
                           isinstance(self._tree.child(2), NonTerminal) and \
                           self._tree.child(2).type == 'Term', 'Syntax error'
                    op = self._tree.child(1).text
                    if op == '+':
                        value = self._tree.child(0).value + self._tree.child(2).value
                    else:
                        value = self._tree.child(0).value - self._tree.child(2).value
                    self._tree.value = value
            # Term
            elif self._tree.type == 'Term':
                '''term : term '*' factor | term '/' factor | factor'''
                assert len(self._tree.children) == 1 or len(self._tree.children) == 3, 'Syntax error'
                if len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and self._tree.child(
                        0).type == 'Factor', 'Syntax error'
                    self._tree.value = self._tree.child(0).value
                elif len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and self._tree.child(0).type == 'Term' and \
                           isinstance(self._tree.child(1), Terminal) and \
                           (self._tree.child(1).text in ('*', '/', '//')) and \
                           isinstance(self._tree.child(2), NonTerminal) and self._tree.child(
                        2).type == 'Factor', 'Syntax error'
                    op = self._tree.child(1).text
                    if op == '*':
                        value = self._tree.child(0).value * self._tree.child(2).value
                    else:
                        assert self._tree.child(2).value != 0, '除数不能为0'
                        if op == '//':
                            value = self._tree.child(0).value // self._tree.child(2).value
                        else:
                            value = self._tree.child(0).value / self._tree.child(2).value
                    self._tree.value = value
            # Factor
            elif self._tree.type == 'Factor':
                """factor : leftval | NUMBER | len | '(' expr ')'"""
                assert len(self._tree.children) == 1 or len(self._tree.children) == 3, 'Syntax error'
                if len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), LeftValue) or \
                           (isinstance(self._tree.child(0), NonTerminal) and self._tree.child(0).type == 'Len') or \
                           isinstance(self._tree.child(0), Number), 'Syntax error'
                    if isinstance(self._tree.child(0), LeftValue):  # leftval
                        value = self.get_value(self.var_table, self._tree.child(0).id)  # search for var_table
                        assert value is not None, f'符号 "{self._tree.child(0).id}" 未定义'
                        self._tree.value = value
                    elif isinstance(self._tree.child(0), NonTerminal):
                        self._tree.value = self._tree.child(0).value
                    else:
                        self._tree.value = self._tree.child(0).value
                elif len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == '(' and \
                           isinstance(self._tree.child(1), NonTerminal) and self._tree.child(1).type == 'Expr' and \
                           isinstance(self._tree.child(2), Terminal) and self._tree.child(2).text == ')', 'Syntax error'
                    self._tree.value = self._tree.child(1).value
            # Exprs
            elif self._tree.type == 'Exprs':
                """exprs : exprs ',' expr | expr"""
                assert len(self._tree.children) == 1 or len(self._tree.children) == 3, 'Syntax error'
                if len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Expr', 'Syntax error'
                    self._tree.value = [self._tree.child(0).value]
                elif len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and self._tree.child(0).type == 'Exprs' and \
                           isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == ',' and \
                           isinstance(self._tree.child(2), NonTerminal) and \
                           self._tree.child(2).type == 'Expr', 'Syntax error'
                    self._tree.value = self._tree.child(0).value + [self._tree.child(2).value]
            # Print
            elif self._tree.type == 'Print':
                ''' print : PRINT '(' exprs ')' | PRINT '(' ')' '''
                assert (len(self._tree.children) == 4 and
                        isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'print' and
                        isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '(' and
                        isinstance(self._tree.child(2), NonTerminal) and self._tree.child(2).type == 'Exprs' and
                        isinstance(self._tree.child(3), Terminal) and self._tree.child(3).text == ')') or \
                       (len(self._tree.children) == 3 and
                        isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'print' and
                        isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '(' and
                        isinstance(self._tree.child(2), Terminal) and self._tree.child(2).text == ')'), 'Syntax error'
                if len(self._tree.children) == 4:
                    print(*self._tree.child(2).value)
                else:
                    print()
            # Len
            elif self._tree.type == 'Len':
                """len -> LEN '(' leftval ')'  { len.value = len(leftval.value) }"""
                assert len(self._tree.children) == 4 and \
                       isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == 'len' and \
                       isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == '(' and \
                       isinstance(self._tree.child(2), LeftValue) and \
                       isinstance(self._tree.child(3), Terminal) and self._tree.child(3).text == ')', 'Syntax error'
                value = self.get_value(self.var_table, self._tree.child(2).id)
                self._tree.value = len(value)
            # Array
            elif self._tree.type == 'Array':
                ''' array : '[' exprs ']' | '[' ']' '''
                assert (len(self._tree.children) == 3 and
                        isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == '[' and
                        isinstance(self._tree.child(1), NonTerminal) and self._tree.child(1).type == 'Exprs' and
                        isinstance(self._tree.child(2), Terminal) and self._tree.child(2).text == ']') or \
                       (len(self._tree.children) == 2 and
                        isinstance(self._tree.child(0), Terminal) and self._tree.child(0).text == '[' and
                        isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == ']'), 'Syntax error'
                if len(self._tree.children) == 3:
                    self._tree.value = list(self._tree.child(1).value)
                else:
                    self._tree.value = []
            # SelfVar
            elif self._tree.type == 'SelfVar':
                """{ leftval.value = leftval.value + 1; set_value(var_table, leftval.id, leftval.value); }
                   { leftval.value = leftval.value - 1; set_value(var_table, leftval.id, leftval.value); }"""
                assert len(self._tree.children) == 2 and \
                       isinstance(self._tree.child(0), LeftValue) and \
                       isinstance(self._tree.child(1), Terminal) and \
                       self._tree.child(1).text in ('++', '--'), 'Syntax error'
                value = self.get_value(self.var_table, self._tree.child(0).id)
                if self._tree.child(1).text == '++':
                    value = value + 1
                    if DEBUG_MODE: print('SelfVar', self._tree.child(0).id, '++', value)
                elif self._tree.child(1).text == '--':
                    value = value - 1
                    if DEBUG_MODE: print('SelfVar', self._tree.child(0).id, '--', value)
                self.set_value(self.var_table, self._tree.child(0).id, value)
            # Condition
            elif self._tree.type == 'Condition':
                """ condition : condition OR join | join """
                assert len(self._tree.children) == 3 or len(self._tree.children) == 1, 'Syntax error'
                if len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Condition' and \
                           isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == 'or' and \
                           isinstance(self._tree.child(2), NonTerminal) and \
                           self._tree.child(2).type == 'Join', 'Syntax error'
                    self._tree.value = self._tree.child(0).value or self._tree.child(2).value
                elif len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Join', 'Syntax error'
                    self._tree.value = self._tree.child(0).value
            # Join
            elif self._tree.type == 'Join':
                """ join : join AND equality | equality """
                assert len(self._tree.children) == 3 or len(self._tree.children) == 1, 'Syntax error'
                if len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Join' and \
                           isinstance(self._tree.child(1), Terminal) and self._tree.child(1).text == 'and' and \
                           isinstance(self._tree.child(2), NonTerminal) and \
                           self._tree.child(2).type == 'Equality', 'Syntax error'
                    self._tree.value = self._tree.child(0).value and self._tree.child(2).value
                elif len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Equality', 'Syntax error'
                    self._tree.value = self._tree.child(0).value
            # Equality
            elif self._tree.type == 'Equality':
                """ equality : equality EQ rel | equality NE rel | rel
                    rel : expr LT expr | expr LE expr | expr GT expr | expr GE expr | expr """
                assert len(self._tree.children) == 3 or len(self._tree.children) == 1, 'Syntax error'
                if len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Equality' and \
                           isinstance(self._tree.child(1), Terminal) and \
                           self._tree.child(1).text in ('==', '!=') and \
                           isinstance(self._tree.child(2), NonTerminal) and \
                           self._tree.child(2).type == 'Relation', 'Syntax error'
                    if self._tree.child(1).text == '==':
                        self._tree.value = self._tree.child(0).value == self._tree.child(2).value
                    elif self._tree.child(1).text == '!=':
                        self._tree.value = self._tree.child(0).value != self._tree.child(2).value
                elif len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Relation', 'Syntax error'
                    self._tree.value = self._tree.child(0).value
            # Relation
            elif self._tree.type == 'Relation':
                """ rel : expr LT expr | expr LE expr | expr GT expr | expr GE expr | expr """
                assert len(self._tree.children) == 3 or len(self._tree.children) == 1, 'Syntax error'
                if len(self._tree.children) == 3:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Expr' and \
                           isinstance(self._tree.child(1), Terminal) and \
                           self._tree.child(1).text in ('<', '<=', '>', '>=') and \
                           isinstance(self._tree.child(2), NonTerminal) and \
                           self._tree.child(2).type == 'Expr', 'Syntax error'
                    if self._tree.child(1).text == '<':
                        self._tree.value = self._tree.child(0).value < self._tree.child(2).value
                    elif self._tree.child(1).text == '<=':
                        self._tree.value = self._tree.child(0).value <= self._tree.child(2).value
                    elif self._tree.child(1).text == '>':
                        self._tree.value = self._tree.child(0).value > self._tree.child(2).value
                    elif self._tree.child(1).text == '>=':
                        self._tree.value = self._tree.child(0).value >= self._tree.child(2).value
                elif len(self._tree.children) == 1:
                    assert isinstance(self._tree.child(0), NonTerminal) and \
                           self._tree.child(0).type == 'Expr', 'Syntax error'
                    self._tree.value = bool(self._tree.child(0).value)
                if DEBUG_MODE: print('condition:', self._tree.value)
