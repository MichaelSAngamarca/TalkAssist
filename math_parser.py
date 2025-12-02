import re
from word2number import w2n

class MathParser:
    def __init__(self):
        # Words replaced by math symbols
        self.replacements = {
            "plus": "+",
            "minus": "-",
            "multiplied by": "*",
            "times": "*",
            "x": "*",
            "divided by": "/",
            "over": "/",
        }

        # Trigger phrases for math questions
        self.triggers = [
            "calculate", "compute", "solve", "find",
            "equal", "equals", "what is", "what's"
        ]

    def is_math_expression(self, text):
        text_low = text.lower()
        if re.search(r"\b(time|date|day|month|year)\b", text_low):
            return False
        for phrase in list(self.replacements.keys()) + self.triggers + ["sum of", "product of", "difference of", "quotient of"]:
            if re.search(rf"\b{re.escape(phrase)}\b", text_low):
                return True
        return False

    def parse_and_calculate(self, text):
        """Convert text-based math into numeric expression and evaluate it."""
        text_low = text.lower()

        #Remove triggers like "what is", "calculate", etc.
        text_low = re.sub(
            r"\b(" + "|".join(map(re.escape, self.triggers)) + r")\b",
            "",
            text_low
        )

        # Handle phrases like "sum/product/difference/quotient of X and Y"
        pattern = r"(sum|product|difference|quotient) of ([\w\s]+?) and ([\w\s]+)"
        def replace_math_phrases(match):
            op = match.group(1)
            a, b = match.group(2), match.group(3)
            ops = {"sum": "+", "product": "*", "difference": "-", "quotient": "/"}
            return f"{a} {ops[op]} {b}"
        text_low = re.sub(pattern, replace_math_phrases, text_low)

        #Replace math words with symbols
        for word, symbol in sorted(self.replacements.items(), key=lambda x: -len(x[0])):
            text_low = re.sub(rf"\b{word}\b", f" {symbol} ", text_low)

        #Convert written numbers (e.g. "five") to digits
        words = text_low.split()
        converted = []
        for w in words:
            if w in {"+", "-", "*", "/"}:
                converted.append(w)
                continue
            clean = re.sub(r"[^\w-]", "", w)
            if not clean:
                continue
            try:
                converted.append(str(w2n.word_to_num(clean)))
            except ValueError:
                converted.append(clean)

        #Clean expression
        expr = " ".join(converted)
        expr = expr.replace("and", "").replace("of", "")
        expr = re.sub(r"[^\d\+\-\*\/\.\s]", "", expr).strip()

        if not expr:
            raise ValueError("Empty or invalid math expression")

       # Evaluate safely
        try:
            result = eval(expr)
            return round(result, 2)
        except Exception as e:
            raise ValueError(f"Error evaluating: {e}")
