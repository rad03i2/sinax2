# -*- coding: utf-8 -*-
"""
SINAX Mathematical Tiny Lab
Scientific calculator using safe Abstract Syntax Tree (AST) evaluator without eval(),
supporting trigonometric functions, logarithms, roots, constants, and programmer calculator modes.
"""

import ast
import math
import operator
from typing import Any, Dict, List, Optional, Tuple


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

MATH_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "ln": math.log,
    "exp": math.exp,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "degrees": math.degrees,
    "radians": math.radians,
    "deg": math.degrees,
    "rad": math.radians,
}

MATH_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


class CalculatorTools:
    """Safe mathematical expression evaluation and programmer tools."""

    _session_history: List[Tuple[str, str]] = []

    @staticmethod
    def _eval_node(node: ast.AST) -> float:
        """Recursively evaluates whitelisted AST nodes safely."""
        if isinstance(node, ast.Constant): # Python 3.8+ numbers/constants
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"قيمة غير مدعومة: {node.value}")

        elif isinstance(node, ast.Name):
            name = node.id.lower()
            if name in MATH_CONSTANTS:
                return float(MATH_CONSTANTS[name])
            raise ValueError(f"متغير غير معروف: {node.id}")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in ALLOWED_OPERATORS:
                raise ValueError(f"عملية غير مدعومة: {op_type.__name__}")
            left = CalculatorTools._eval_node(node.left)
            right = CalculatorTools._eval_node(node.right)
            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("القسمة على صفر غير معرفة رياضياً.")
            return ALLOWED_OPERATORS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in ALLOWED_OPERATORS:
                raise ValueError(f"عملية غير مدعومة: {op_type.__name__}")
            operand = CalculatorTools._eval_node(node.operand)
            return ALLOWED_OPERATORS[op_type](operand)

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("استدعاء غير مسموح به.")
            func_name = node.func.id.lower()
            if func_name not in MATH_FUNCTIONS:
                raise ValueError(f"دالة رياضية غير معروفة: {node.func.id}")

            args = [CalculatorTools._eval_node(arg) for arg in node.args]
            fn = MATH_FUNCTIONS[func_name]
            try:
                return float(fn(*args))
            except Exception as e:
                raise ValueError(f"خطأ في تنفيذ {func_name}: {e}")

        raise ValueError(f"بنية تعبير غير مسموح بها: {type(node).__name__}")

    @staticmethod
    def evaluate_expression(expr: str) -> Dict[str, Any]:
        """
        Parses and evaluates mathematical expression securely via AST.
        NEVER executes eval(), exec(), or arbitrary Python code.
        """
        clean = expr.strip()
        if not clean:
            return {"is_valid": False, "error": "التعبير الرياضي فارغ", "result": ""}

        # Clean Arabic characters and standardize symbols
        standardized = (
            clean.replace("×", "*")
            .replace("÷", "/")
            .replace("π", "pi")
            .replace("^", "**")
        )

        try:
            tree = ast.parse(standardized, mode="eval")
            result_val = CalculatorTools._eval_node(tree.body)

            # Format nicely
            if abs(result_val - round(result_val)) < 1e-12:
                formatted = str(int(round(result_val)))
            else:
                formatted = f"{result_val:,.8g}"

            CalculatorTools._session_history.append((clean, formatted))
            return {
                "is_valid": True,
                "error": "",
                "result": formatted,
                "raw_float": result_val,
            }
        except ZeroDivisionError as e:
            return {"is_valid": False, "error": str(e), "result": ""}
        except (ValueError, SyntaxError) as e:
            return {"is_valid": False, "error": f"صيغة غير صالحة: {e}", "result": ""}
        except Exception as e:
            return {"is_valid": False, "error": f"تعذر حساب التعبير: {e}", "result": ""}

    @staticmethod
    def get_history() -> List[Tuple[str, str]]:
        return list(reversed(CalculatorTools._session_history[-20:]))
