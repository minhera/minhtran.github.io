import sys
import itertools
import string
from wordfreq import top_n_list

# Load English words
eng_words = [word.lower() for word in top_n_list('en', 50000) if word.isalpha()]
eng_words = list(set(eng_words))

# Global variables
variables = {}
rules = []
file_labels = {}

def count_characters(s):
    return f"{len(s)} characters"

def count_words(s):
    return f"{len(s.split())} words"

def count_sentences(s):
    return f"{sum(s.count(p) for p in '.!?')} sentences"

def used_letters(s):
    return ''.join(sorted(set(filter(str.isalpha, s.lower()))))

def unscramble(s):
    s = ''.join(filter(str.isalpha, s.lower()))
    perms = set(''.join(p) for p in itertools.permutations(s))
    return sorted(set(p for p in perms if p in eng_words))

def wordle(base, length, exclude=None, pattern=None, max_words=10):
    base = ''.join(filter(str.isalpha, base.lower()))
    required_letters = set(base)
    base_counts = {c: base.count(c) for c in base}
    exclude_letters = set(exclude.lower()) if exclude else set()
    results = []

    for word in eng_words:
        word = word.lower()
        if len(word) != length or not word.isalpha():
            continue
        if any(c in exclude_letters for c in word):
            continue
        if pattern:
            if len(pattern) != length:
                continue
            if any(p != '_' and word[i] != p for i, p in enumerate(pattern)):
                continue
        if not required_letters.issubset(set(word)):
            continue
        word_counts = {c: word.count(c) for c in word}
        extra_chars = []
        for c in word_counts:
            allowed = base_counts.get(c, 0)
            if word_counts[c] > allowed:
                extra_chars.extend([c] * (word_counts[c] - allowed))
            if c not in base_counts:
                extra_chars.append(c)
        results.append((word, ''.join(sorted(set(extra_chars)))))
        if len(results) >= max_words:
            break
    return results

def count_occurrences(term, text):
    term = term.lower()
    text_lower = text.lower()
    if len(term) == 1:
        count = text_lower.count(term)
    else:
        words = text_lower.split()
        count = sum(1 for word in words if word == term)
    return count

def remove_word(text, word_to_remove):
    word_to_remove = word_to_remove.lower()
    words = text.split()
    filtered = [w for w in words if w.lower() != word_to_remove]
    return ' '.join(filtered)

# Main line processor
def process_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return

    if line.startswith("save "):
        if ' to ' in line:
            parts = line.split(' to ')
            string_part = parts[0][5:].strip()
            filename = parts[1].strip()

            if string_part.startswith('"') and string_part.endswith('"'):
                content = string_part[1:-1]
            elif string_part in variables:
                content = variables[string_part]
            else:
                print(f"Undefined string or variable: {string_part}")
                return

            try:
                with open(filename, "w") as f:
                    f.write(content)
                print(f"Saved to {filename}")
            except Exception as e:
                print(f"Failed to save file: {e}")
        return

    if line.startswith("string ") or line.startswith("file "):
        parts = line.split("=", 1)
        if len(parts) == 2:
            left, value = parts
            parts2 = left.strip().split()
            if len(parts2) == 2:
                var_type, var_name = parts2
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                if var_type == "file":
                    try:
                        with open(value) as f:
                            variables[var_name] = f.read().strip()
                            file_labels[var_name] = value
                    except FileNotFoundError:
                        print(f"File not found: {value}")
                        variables[var_name] = ""
                        file_labels[var_name] = value
                else:
                    variables[var_name] = value
                    file_labels[var_name] = var_name
                return

    if line.startswith("rule "):
        parts = line.split()
        if len(parts) >= 5 and parts[2].isdigit() and "print" in parts:
            keyword = parts[1]
            number = int(parts[2])
            message_index = line.find('print "') + 7
            message = line[message_index:-1]
            op_map = {
                "lessthan": "<",
                "morethan": ">",
                "equal": "=="
            }
            op = op_map.get(keyword)
            if op:
                rules.append((op, number, message))
            return

    if line.startswith("for sentence in "):
        var_name = line.split()[-1]
        content = variables.get(var_name, "")
        sentence_endings = [".", "!", "?"]
        sentences = []
        temp = ""

        for char in content:
            temp += char
            if char in sentence_endings:
                sentences.append(temp.strip())
                temp = ""
        if temp.strip():
            sentences.append(temp.strip())

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_clean = sentence.translate(str.maketrans('', '', string.punctuation))
            word_count = len(sentence_clean.split())
            matched = False
            for op, number, message in rules:
                if (
                    (op == "<" and word_count < number) or
                    (op == ">" and word_count > number) or
                    (op == "==" and word_count == number)
                ):
                    print(message)
                    matched = True
                    break
            if not matched:
                print(sentence_clean)
        return

    if line.startswith("count "):
        parts = line.split()
        if len(parts) >= 3:
            term = parts[1].strip('"')
            var_name = parts[2]
            if var_name not in variables:
                print(f"Undefined variable: {var_name}")
                return
            content = variables[var_name]
            label = file_labels.get(var_name, var_name)
            count = count_occurrences(term, content)
            print(f"{count} {term} in {label}")
            return

    if line.startswith("removeword "):
        parts = line.split()
        if len(parts) >= 3:
            word = parts[1].strip('"')
            var_name = parts[2]
            if var_name in variables:
                new_text = remove_word(variables[var_name], word)
                variables[var_name] = new_text
                print(f"{word} removed from {var_name}")
            else:
                print(f"Undefined variable: {var_name}")
            return

    parts = line.split()
    if parts:
        func = parts[0]
        if func in ["cchar", "cword", "csent", "used", "unscramble", "wordle"]:
            value = ""
            if len(parts) >= 2:
                arg = parts[1]
                if arg.startswith('"') and arg.endswith('"'):
                    value = arg[1:-1]
                else:
                    value = variables.get(arg, "")
            if not value:
                print(f"Undefined or empty value: {arg}")
                return
            if func == "cchar":
                print(count_characters(value))
            elif func == "cword":
                print(count_words(value))
            elif func == "csent":
                print(count_sentences(value))
            elif func == "used":
                print(used_letters(value))
            elif func == "unscramble":
                for w in unscramble(value):
                    print(w)
            elif func == "wordle":
                length = None
                exclude = None
                pattern = None

                if "withlength" in parts:
                    i = parts.index("withlength")
                    if i + 1 < len(parts):
                        length = int(parts[i + 1])

                if "exclude" in parts:
                    i = parts.index("exclude")
                    if i + 1 < len(parts):
                        exclude = parts[i + 1]

                if "pattern" in parts:
                    i = parts.index("pattern")
                    if i + 1 < len(parts):
                        pattern = parts[i + 1]

                if not length:
                    print("Missing or invalid withlength for wordle")
                    return

                results = wordle(value, length, exclude, pattern)
                for word, extra in results:
                    print(f"{word} (extra: {extra})" if extra else word)

            return

    if line in variables:
        print(variables[line])
        return

    print(f"Syntax error or undefined variable: {line}")

def main():
    global rules
    rules = []
    if len(sys.argv) < 2:
        print("Usage: python interpreter.py input.wfl")
        return
    with open(sys.argv[1]) as f:
        for line in f:
            process_line(line)

if __name__ == "__main__":
    main()
