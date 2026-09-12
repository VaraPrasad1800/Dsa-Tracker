"""
Problem statement normalizer and structured section parser.

Converts raw/scraped problem text into clean typography and structured data:
- Problem Description paragraphs (without broken newline splits)
- Examples: list of { input, output, explanation }
- Constraints: list of clean constraint strings
"""
import re


def clean_broken_newlines(text: str) -> str:
    """
    Heuristically repair text where inline tags or BS4 get_text(separator='\\n')
    split words, sentences, or bracket indices across newlines.
    """
    if not text:
        return ''

    # Normalize Windows line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Fix broken bracket indices like nums[\n0\n] -> nums[0], [\n0\n,\n1\n] -> [0, 1]
    text = re.sub(r'\[\s*\n\s*(\w+)\s*\n\s*\]', r'[\1]', text)
    text = re.sub(r'\[\s*(\w+)\s*\n\s*\]', r'[\1]', text)
    text = re.sub(r'\[\s*\n\s*(\w+)\s*\]', r'[\1]', text)
    text = re.sub(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', r'[\1, \2]', text)

    # Split into paragraphs by double newlines
    paragraphs = re.split(r'\n\s*\n+', text)
    cleaned_paragraphs = []

    for para in paragraphs:
        lines = [ln.strip() for ln in para.split('\n') if ln.strip()]
        if not lines:
            continue

        # If this paragraph is code or preformatted, preserve newlines
        first_line = lines[0]
        if (
            first_line.startswith(('```', 'Input:', 'Output:', 'Example', 'Constraints:', 'Note:'))
            or any(l.startswith(('-', '*', '•', '1.', '2.', '3.')) for l in lines)
        ):
            cleaned_paragraphs.append('\n'.join(lines))
            continue

        # Otherwise, join broken sentence lines into flowing prose
        flowing_words = []
        for line in lines:
            # Strip excessive internal spaces
            cleaned_line = re.sub(r'[ \t]+', ' ', line)
            flowing_words.append(cleaned_line)

        joined_para = ' '.join(flowing_words)
        # Clean up punctuation spacing: e.g. "word , word" -> "word, word"
        joined_para = re.sub(r'\s+([,.:;?!])', r'\1', joined_para)
        # Clean array formatting: "[ 0 , 1 ]" -> "[0, 1]"
        joined_para = re.sub(r'\[\s+', '[', joined_para)
        joined_para = re.sub(r'\s+\]', ']', joined_para)
        joined_para = re.sub(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', r'[\1, \2]', joined_para)

        cleaned_paragraphs.append(joined_para)

    return '\n\n'.join(cleaned_paragraphs).strip()


def parse_structured_statement(text: str) -> dict:
    """
    Parse a problem statement into structured sections:
    - description: clean markdown/text of the core description
    - examples: list of { 'input': str, 'output': str, 'explanation': str }
    - constraints: list of constraint strings
    """
    if not text:
        return {'description': '', 'examples': [], 'constraints': []}

    cleaned = clean_broken_newlines(text)

    # Split off Constraints section if present
    constraints = []
    constraints_match = re.search(
        r'(?:^|\n)\s*(?:Constraints|Note|Notes):\s*\n?(.*)$',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if constraints_match:
        constraints_raw = constraints_match.group(1).strip()
        cleaned = cleaned[:constraints_match.start()].strip()
        for line in constraints_raw.split('\n'):
            line = line.strip().lstrip('-*• \t')
            if line:
                constraints.append(line)

    # Split into core description and examples
    examples = []
    # Pattern to find Example sections (e.g. "Example 1:", "Example:")
    example_pattern = re.compile(
        r'(?:^|\n)\s*(?:Example\s*(\d*)|Examples):\s*\n?',
        flags=re.IGNORECASE,
    )

    example_splits = list(example_pattern.finditer(cleaned))
    if example_splits:
        # Everything before the first Example is the problem description
        first_ex_pos = example_splits[0].start()
        description = cleaned[:first_ex_pos].strip()
        examples_block = cleaned[first_ex_pos:].strip()

        # Parse individual examples
        ex_blocks = re.split(r'(?:^|\n)\s*(?:Example\s*\d*|Examples):\s*\n?', examples_block, flags=re.IGNORECASE)
        for block in ex_blocks:
            block = block.strip()
            if not block:
                continue

            input_val = ''
            output_val = ''
            explanation_val = ''

            # Extract Input
            in_match = re.search(r'(?:Input:\s*|Given\s+)(.+?)(?=(?:Output:|Because|return|\Z))', block, flags=re.IGNORECASE | re.DOTALL)
            if in_match:
                input_val = in_match.group(1).strip().rstrip(',').strip()

            # Extract Output
            out_match = re.search(r'(?:Output:\s*|return\s+)(.+?)(?=(?:Explanation:|Because|\Z))', block, flags=re.IGNORECASE | re.DOTALL)
            if out_match:
                output_val = out_match.group(1).strip().rstrip('.').strip()

            # Extract Explanation
            exp_match = re.search(r'(?:Explanation:\s*|Because\s+)(.+)$', block, flags=re.IGNORECASE | re.DOTALL)
            if exp_match:
                explanation_val = exp_match.group(1).strip()
                if not explanation_val.lower().startswith('because') and 'Because' in block:
                    explanation_val = 'Because ' + explanation_val

            if input_val or output_val:
                examples.append({
                    'input': input_val,
                    'output': output_val,
                    'explanation': explanation_val,
                })
    else:
        description = cleaned

    return {
        'description': description,
        'examples': examples,
        'constraints': constraints,
    }
