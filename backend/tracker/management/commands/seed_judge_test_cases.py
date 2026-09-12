"""
Management command to seed test cases, language templates, execution harnesses,
and editorial solutions for core DSA problems.
"""
from django.core.management.base import BaseCommand
from tracker.models import Problem, TestCase, LanguageTemplate, Solution


class Command(BaseCommand):
    help = 'Seed test cases, starter code templates, harnesses, and solutions for core problems'

    def handle(self, *args, **options):
        self.stdout.write('Seeding core Online Judge problems and test cases...')

        self.seed_two_sum()
        self.seed_longest_palindrome()
        self.seed_atoi()
        self.seed_utf8_validation()

        self.stdout.write(self.style.SUCCESS('Successfully seeded core Online Judge problems!'))

    def seed_two_sum(self):
        p, _ = Problem.objects.get_or_create(
            question_number=1,
            defaults={
                'title': 'Two Sum',
                'slug': 'two-sum',
                'difficulty': 'Easy',
                'leetcode_id': 1,
            }
        )
        p.title = 'Two Sum'
        p.difficulty = 'Easy'
        p.execution_mode = 'FUNCTION'
        p.function_name = 'twoSum'
        p.description = (
            "Given an array of integers `nums` and an integer `target`, return indices "
            "of the two numbers such that they add up to `target`.\n\n"
            "You may assume that each input would have **exactly one solution**, and you "
            "may not use the same element twice.\n\n"
            "You can return the answer in any order."
        )
        p.examples = [
            {
                'input': 'nums = [2,7,11,15], target = 9',
                'output': '[0,1]',
                'explanation': 'Because nums[0] + nums[1] == 9, we return [0, 1].'
            },
            {
                'input': 'nums = [3,2,4], target = 6',
                'output': '[1,2]',
                'explanation': 'Because nums[1] + nums[2] == 6, we return [1, 2].'
            },
            {
                'input': 'nums = [3,3], target = 6',
                'output': '[0,1]',
                'explanation': 'Because nums[0] + nums[1] == 6, we return [0, 1].'
            }
        ]
        p.constraints = [
            '2 <= nums.length <= 10^4',
            '-10^9 <= nums[i] <= 10^9',
            '-10^9 <= target <= 10^9',
            'Only one valid answer exists.'
        ]
        p.save()

        # Test cases
        TestCase.objects.filter(problem=p).delete()
        test_cases = [
            # Visible samples
            (False, '[2, 7, 11, 15]\n9', '[0, 1]', 1),
            (False, '[3, 2, 4]\n6', '[1, 2]', 2),
            (False, '[3, 3]\n6', '[0, 1]', 3),
            # Hidden tests
            (True, '[-1, -2, -3, -4, -5]\n-8', '[2, 4]', 4),
            (True, '[0, 4, 3, 0]\n0', '[0, 3]', 5),
            (True, '[1000000000, 3, -1000000000]\n0', '[0, 2]', 6),
            (True, '[1, 5, 8, 12, 19, 25]\n30', '[1, 5]', 7),
        ]
        for is_hidden, in_txt, out_txt, ord_num in test_cases:
            TestCase.objects.create(
                problem=p,
                is_hidden=is_hidden,
                input_text=in_txt,
                expected_output=out_txt,
                order=ord_num,
            )

        # Language templates & harnesses
        # 1. Python
        py_starter = (
            "class Solution:\n"
            "    def twoSum(self, nums: list[int], target: int) -> list[int]:\n"
            "        # Write your solution here\n"
            "        pass\n"
        )
        py_harness = (
            "if __name__ == '__main__':\n"
            "    import sys, json\n"
            "    lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]\n"
            "    if len(lines) >= 2:\n"
            "        nums = json.loads(lines[0])\n"
            "        target = int(lines[1])\n"
            "        sol = Solution()\n"
            "        res = sol.twoSum(nums, target)\n"
            "        print(json.dumps(res))\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='python',
            defaults={'starter_code': py_starter, 'harness_code': py_harness}
        )

        # 2. C++
        cpp_starter = (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "class Solution {\n"
            "public:\n"
            "    vector<int> twoSum(vector<int>& nums, int target) {\n"
            "        // Write your solution here\n"
            "        return {};\n"
            "    }\n"
            "};\n"
        )
        cpp_harness = (
            "#ifndef MAIN_DEFINED\n"
            "#include <iostream>\n"
            "#include <string>\n"
            "#include <sstream>\n"
            "#include <vector>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    ios_base::sync_with_stdio(false);\n"
            "    cin.tie(NULL);\n"
            "    string line1, line2;\n"
            "    if (!getline(cin, line1)) return 0;\n"
            "    while (line1.empty() && getline(cin, line1));\n"
            "    if (!getline(cin, line2)) return 0;\n"
            "    while (line2.empty() && getline(cin, line2));\n\n"
            "    vector<int> nums;\n"
            "    for (char &c : line1) { if (c == '[' || c == ']' || c == ',') c = ' '; }\n"
            "    stringstream ss1(line1);\n"
            "    int val;\n"
            "    while (ss1 >> val) nums.push_back(val);\n\n"
            "    stringstream ss2(line2);\n"
            "    int target;\n"
            "    ss2 >> target;\n\n"
            "    Solution sol;\n"
            "    vector<int> res = sol.twoSum(nums, target);\n"
            "    cout << \"[\";\n"
            "    for (size_t i = 0; i < res.size(); ++i) {\n"
            "        cout << res[i] << (i + 1 < res.size() ? \", \" : \"\");\n"
            "    }\n"
            "    cout << \"]\" << endl;\n"
            "    return 0;\n"
            "}\n"
            "#endif\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='cpp',
            defaults={'starter_code': cpp_starter, 'harness_code': cpp_harness}
        )

        # 3. C
        c_starter = (
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n\n"
            "/**\n"
            " * Note: The returned array must be malloced, assume caller calls free().\n"
            " */\n"
            "int* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n"
            "    // Write your solution here\n"
            "    *returnSize = 0;\n"
            "    return NULL;\n"
            "}\n"
        )
        c_harness = (
            "#ifndef MAIN_DEFINED\n"
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n\n"
            "int main() {\n"
            "    char line1[8192], line2[256];\n"
            "    if (!fgets(line1, sizeof(line1), stdin)) return 0;\n"
            "    if (!fgets(line2, sizeof(line2), stdin)) return 0;\n\n"
            "    int nums[2048];\n"
            "    int numsSize = 0;\n"
            "    char *p = line1;\n"
            "    while (*p) {\n"
            "        while (*p && (*p == '[' || *p == ']' || *p == ',' || *p == ' ' || *p == '\\t' || *p == '\\n' || *p == '\\r')) p++;\n"
            "        if (!*p) break;\n"
            "        int num, chars_read;\n"
            "        if (sscanf(p, \"%d%n\", &num, &chars_read) == 1) {\n"
            "            nums[numsSize++] = num;\n"
            "            p += chars_read;\n"
            "        } else { p++; }\n"
            "    }\n"
            "    int target = 0;\n"
            "    sscanf(line2, \"%d\", &target);\n"
            "    int returnSize = 0;\n"
            "    int* res = twoSum(nums, numsSize, target, &returnSize);\n"
            "    printf(\"[\");\n"
            "    for (int i = 0; i < returnSize; i++) {\n"
            "        printf(\"%d%s\", res[i], (i + 1 < returnSize ? \", \" : \"\"));\n"
            "    }\n"
            "    printf(\"]\\n\");\n"
            "    if (res) free(res);\n"
            "    return 0;\n"
            "}\n"
            "#endif\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='c',
            defaults={'starter_code': c_starter, 'harness_code': c_harness}
        )

        # 4. Java
        java_starter = (
            "import java.util.*;\n\n"
            "class Solution {\n"
            "    public int[] twoSum(int[] nums, int target) {\n"
            "        // Write your solution here\n"
            "        return new int[0];\n"
            "    }\n"
            "}\n"
        )
        java_harness = (
            "class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Scanner sc = new Scanner(System.in);\n"
            "        if (!sc.hasNextLine()) return;\n"
            "        String line1 = sc.nextLine().trim();\n"
            "        while (line1.isEmpty() && sc.hasNextLine()) line1 = sc.nextLine().trim();\n"
            "        if (!sc.hasNextLine()) return;\n"
            "        String line2 = sc.nextLine().trim();\n\n"
            "        line1 = line1.replace(\"[\", \" \").replace(\"]\", \" \").replace(\",\", \" \");\n"
            "        Scanner s1 = new Scanner(line1);\n"
            "        List<Integer> list = new ArrayList<>();\n"
            "        while (s1.hasNextInt()) list.add(s1.nextInt());\n"
            "        int[] nums = new int[list.size()];\n"
            "        for (int i = 0; i < list.size(); i++) nums[i] = list.get(i);\n"
            "        int target = Integer.parseInt(line2.trim());\n\n"
            "        Solution sol = new Solution();\n"
            "        int[] res = sol.twoSum(nums, target);\n"
            "        System.out.print(\"[\");\n"
            "        for (int i = 0; i < res.length; i++) {\n"
            "            System.out.print(res[i] + (i + 1 < res.length ? \", \" : \"\"));\n"
            "        }\n"
            "        System.out.println(\"]\");\n"
            "    }\n"
            "}\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='java',
            defaults={'starter_code': java_starter, 'harness_code': java_harness}
        )

        # Editorial Solution
        sol_codes = {
            'python': (
                "class Solution:\n"
                "    def twoSum(self, nums: list[int], target: int) -> list[int]:\n"
                "        seen = {}\n"
                "        for i, num in enumerate(nums):\n"
                "            complement = target - num\n"
                "            if complement in seen:\n"
                "                return [seen[complement], i]\n"
                "            seen[num] = i\n"
                "        return []\n"
            ),
            'cpp': (
                "#include <vector>\n"
                "#include <unordered_map>\n"
                "using namespace std;\n\n"
                "class Solution {\n"
                "public:\n"
                "    vector<int> twoSum(vector<int>& nums, int target) {\n"
                "        unordered_map<int, int> seen;\n"
                "        for (int i = 0; i < (int)nums.size(); ++i) {\n"
                "            int complement = target - nums[i];\n"
                "            if (seen.find(complement) != seen.end()) {\n"
                "                return {seen[complement], i};\n"
                "            }\n"
                "            seen[nums[i]] = i;\n"
                "        }\n"
                "        return {};\n"
                "    }\n"
                "};\n"
            ),
            'java': (
                "import java.util.HashMap;\n"
                "import java.util.Map;\n\n"
                "class Solution {\n"
                "    public int[] twoSum(int[] nums, int target) {\n"
                "        Map<Integer, Integer> seen = new HashMap<>();\n"
                "        for (int i = 0; i < nums.length; i++) {\n"
                "            int complement = target - nums[i];\n"
                "            if (seen.containsKey(complement)) {\n"
                "                return new int[]{seen.get(complement), i};\n"
                "            }\n"
                "            seen.put(nums[i], i);\n"
                "        }\n"
                "        return new int[0];\n"
                "    }\n"
                "}\n"
            ),
            'c': (
                "#include <stdlib.h>\n\n"
                "int* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n"
                "    int* result = (int*)malloc(2 * sizeof(int));\n"
                "    *returnSize = 2;\n"
                "    for (int i = 0; i < numsSize; i++) {\n"
                "        for (int j = i + 1; j < numsSize; j++) {\n"
                "            if (nums[i] + nums[j] == target) {\n"
                "                result[0] = i;\n"
                "                result[1] = j;\n"
                "                return result;\n"
                "            }\n"
                "        }\n"
                "    }\n"
                "    *returnSize = 0;\n"
                "    return NULL;\n"
                "}\n"
            )
        }
        Solution.objects.update_or_create(
            problem=p,
            defaults={
                'question_number': 1,
                'title': 'Two Sum',
                'description': p.description,
                'code': sol_codes['python'],
                'code_by_language': sol_codes,
                'language': 'python',
                'explanation': (
                    "### One-pass Hash Table Approach\n\n"
                    "We iterate through the array once while maintaining a hash map `seen` storing each number's value "
                    "mapped to its index.\n\n"
                    "For each element `num` at index `i`:\n"
                    "1. Calculate the required `complement = target - num`.\n"
                    "2. If `complement` already exists in `seen`, return `[seen[complement], i]`.\n"
                    "3. Otherwise, record `seen[num] = i` and continue."
                ),
                'time_complexity': 'O(N)',
                'space_complexity': 'O(N)',
                'fetch_failed': False,
            }
        )

    def seed_longest_palindrome(self):
        p, _ = Problem.objects.get_or_create(
            question_number=5,
            defaults={
                'title': 'Longest Palindromic Substring',
                'slug': 'longest-palindromic-substring',
                'difficulty': 'Medium',
                'leetcode_id': 5,
            }
        )
        p.title = 'Longest Palindromic Substring'
        p.difficulty = 'Medium'
        p.execution_mode = 'FUNCTION'
        p.function_name = 'longestPalindrome'
        p.description = (
            "Given a string `s`, return the longest palindromic substring in `s`."
        )
        p.examples = [
            {
                'input': 's = "babad"',
                'output': '"bab"',
                'explanation': '"aba" is also a valid answer.'
            },
            {
                'input': 's = "cbbd"',
                'output': '"bb"',
                'explanation': 'The longest palindromic substring is "bb".'
            }
        ]
        p.constraints = [
            '1 <= s.length <= 1000',
            's consist of only digits and English letters.'
        ]
        p.save()

        TestCase.objects.filter(problem=p).delete()
        test_cases = [
            (False, 'babad', 'bab|aba', 1),
            (False, 'cbbd', 'bb', 2),
            (True, 'a', 'a', 3),
            (True, 'ac', 'a|c', 4),
            (True, 'racecar', 'racecar', 5),
            (True, 'noon', 'noon', 6),
        ]
        for is_hidden, in_txt, out_txt, ord_num in test_cases:
            TestCase.objects.create(
                problem=p,
                is_hidden=is_hidden,
                input_text=in_txt,
                expected_output=out_txt,
                order=ord_num,
            )

        py_starter = (
            "class Solution:\n"
            "    def longestPalindrome(self, s: str) -> str:\n"
            "        # Write your solution here\n"
            "        pass\n"
        )
        py_harness = (
            "if __name__ == '__main__':\n"
            "    import sys, json\n"
            "    raw = sys.stdin.read().strip()\n"
            "    if raw:\n"
            "        try: s = json.loads(raw)\n"
            "        except Exception: s = raw.strip('\"')\n"
            "        sol = Solution()\n"
            "        res = sol.longestPalindrome(s)\n"
            "        print(res)\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='python',
            defaults={'starter_code': py_starter, 'harness_code': py_harness}
        )

        cpp_starter = (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "class Solution {\n"
            "public:\n"
            "    string longestPalindrome(string s) {\n"
            "        // Write your solution here\n"
            "        return \"\";\n"
            "    }\n"
            "};\n"
        )
        cpp_harness = (
            "#ifndef MAIN_DEFINED\n"
            "#include <iostream>\n"
            "#include <string>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    string s;\n"
            "    if (!(cin >> s)) return 0;\n"
            "    if (s.size() >= 2 && s.front() == '\"' && s.back() == '\"') s = s.substr(1, s.size() - 2);\n"
            "    Solution sol;\n"
            "    string res = sol.longestPalindrome(s);\n"
            "    cout << res << endl;\n"
            "    return 0;\n"
            "}\n"
            "#endif\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='cpp',
            defaults={'starter_code': cpp_starter, 'harness_code': cpp_harness}
        )

        # Editorial Solution
        sol_codes = {
            'python': (
                "class Solution:\n"
                "    def longestPalindrome(self, s: str) -> str:\n"
                "        if not s: return ''\n"
                "        start, end = 0, 0\n"
                "        def expand(l, r):\n"
                "            while l >= 0 and r < len(s) and s[l] == s[r]:\n"
                "                l -= 1\n"
                "                r += 1\n"
                "            return l + 1, r - 1\n"
                "        for i in range(len(s)):\n"
                "            l1, r1 = expand(i, i)\n"
                "            if r1 - l1 > end - start:\n"
                "                start, end = l1, r1\n"
                "            l2, r2 = expand(i, i + 1)\n"
                "            if r2 - l2 > end - start:\n"
                "                start, end = l2, r2\n"
                "        return s[start:end+1]\n"
            ),
            'cpp': (
                "#include <string>\n"
                "using namespace std;\n\n"
                "class Solution {\n"
                "public:\n"
                "    string longestPalindrome(string s) {\n"
                "        if (s.empty()) return \"\";\n"
                "        int start = 0, maxLen = 0;\n"
                "        auto expand = [&](int l, int r) {\n"
                "            while (l >= 0 && r < (int)s.size() && s[l] == s[r]) {\n"
                "                l--; r++;\n"
                "            }\n"
                "            int len = r - l - 1;\n"
                "            if (len > maxLen) {\n"
                "                maxLen = len;\n"
                "                start = l + 1;\n"
                "            }\n"
                "        };\n"
                "        for (int i = 0; i < (int)s.size(); ++i) {\n"
                "            expand(i, i);\n"
                "            expand(i, i + 1);\n"
                "        }\n"
                "        return s.substr(start, maxLen);\n"
                "    }\n"
                "};\n"
            )
        }
        Solution.objects.update_or_create(
            problem=p,
            defaults={
                'question_number': 5,
                'title': 'Longest Palindromic Substring',
                'description': p.description,
                'code': sol_codes['python'],
                'code_by_language': sol_codes,
                'language': 'python',
                'explanation': (
                    "### Expand Around Center Approach\n\n"
                    "A palindrome mirrors around its center. A string of length N has `2N - 1` possible centers "
                    "(N single-character centers for odd palindromes, and N - 1 between-character centers for even palindromes).\n\n"
                    "For each center, expand outward as long as the boundary characters match."
                ),
                'time_complexity': 'O(N^2)',
                'space_complexity': 'O(1)',
                'fetch_failed': False,
            }
        )

    def seed_atoi(self):
        p, _ = Problem.objects.get_or_create(
            question_number=8,
            defaults={
                'title': 'String to Integer (atoi)',
                'slug': 'string-to-integer-atoi',
                'difficulty': 'Medium',
                'leetcode_id': 8,
            }
        )
        p.title = 'String to Integer (atoi)'
        p.difficulty = 'Medium'
        p.execution_mode = 'FUNCTION'
        p.function_name = 'myAtoi'
        p.description = (
            "Implement the `myAtoi(string s)` function, which converts a string to a 32-bit signed integer.\n\n"
            "The algorithm for `myAtoi(string s)` is as follows:\n\n"
            "1. **Whitespace**: Ignore any leading whitespace (`\" \"`).\n"
            "2. **Signedness**: Determine the sign by checking if the next character is `'-'` or `'+'`, assuming positivity if neither present.\n"
            "3. **Conversion**: Read the integer by skipping leading zeros until a non-digit character is encountered or the end of the string is reached.\n"
            "4. **Rounding**: If the integer is out of the 32-bit signed integer range `[-2^31, 2^31 - 1]`, clamp the integer so that it remains in the range."
        )
        p.examples = [
            {
                'input': 's = "42"',
                'output': '42',
                'explanation': 'The underlined characters are what is read in, the caret is the current reader position.'
            },
            {
                'input': 's = "   -042"',
                'output': '-42',
                'explanation': 'Leading whitespace is read and ignored, followed by \'-\', and digits \'042\'.'
            },
            {
                'input': 's = "1337c0d3"',
                'output': '1337',
                'explanation': 'Conversion stops at digit \'c\' as it is non-digit.'
            },
            {
                'input': 's = "0-1"',
                'output': '0',
                'explanation': 'Conversion stops at \'-\' after \'0\'.'
            },
            {
                'input': 's = "words and 987"',
                'output': '0',
                'explanation': 'Reading stops at the first non-digit character \'w\'.'
            }
        ]
        p.constraints = [
            '0 <= s.length <= 200',
            's consists of English letters, digits, \' \', \'+\', \'-\', and \'.\''
        ]
        p.save()

        TestCase.objects.filter(problem=p).delete()
        test_cases = [
            (False, '42', '42', 1),
            (False, '   -042', '-42', 2),
            (False, '1337c0d3', '1337', 3),
            (False, '0-1', '0', 4),
            (True, 'words and 987', '0', 5),
            (True, '-91283472332', '-2147483648', 6),
            (True, '91283472332', '2147483647', 7),
            (True, '+1', '1', 8),
            (True, '+-12', '0', 9),
        ]
        for is_hidden, in_txt, out_txt, ord_num in test_cases:
            TestCase.objects.create(
                problem=p,
                is_hidden=is_hidden,
                input_text=in_txt,
                expected_output=out_txt,
                order=ord_num,
            )

        py_starter = (
            "class Solution:\n"
            "    def myAtoi(self, s: str) -> int:\n"
            "        # Write your solution here\n"
            "        pass\n"
        )
        py_harness = (
            "if __name__ == '__main__':\n"
            "    import sys\n"
            "    raw = sys.stdin.read().strip()\n"
            "    if raw:\n"
            "        s = raw.strip('\"') if (raw.startswith('\"') and raw.endswith('\"')) else raw\n"
            "        sol = Solution()\n"
            "        res = sol.myAtoi(s)\n"
            "        print(res)\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='python',
            defaults={'starter_code': py_starter, 'harness_code': py_harness}
        )

        cpp_starter = (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "class Solution {\n"
            "public:\n"
            "    int myAtoi(string s) {\n"
            "        // Write your solution here\n"
            "        return 0;\n"
            "    }\n"
            "};\n"
        )
        cpp_harness = (
            "#ifndef MAIN_DEFINED\n"
            "#include <iostream>\n"
            "#include <string>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    string s;\n"
            "    getline(cin, s);\n"
            "    if (s.size() >= 2 && s.front() == '\"' && s.back() == '\"') s = s.substr(1, s.size() - 2);\n"
            "    Solution sol;\n"
            "    int res = sol.myAtoi(s);\n"
            "    cout << res << endl;\n"
            "    return 0;\n"
            "}\n"
            "#endif\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='cpp',
            defaults={'starter_code': cpp_starter, 'harness_code': cpp_harness}
        )

        # Editorial Solution
        sol_codes = {
            'python': (
                "class Solution:\n"
                "    def myAtoi(self, s: str) -> int:\n"
                "        s = s.lstrip()\n"
                "        if not s: return 0\n"
                "        sign = 1\n"
                "        i = 0\n"
                "        if s[0] == '+': i += 1\n"
                "        elif s[0] == '-': sign = -1; i += 1\n"
                "        val = 0\n"
                "        INT_MAX = 2**31 - 1\n"
                "        INT_MIN = -2**31\n"
                "        while i < len(s) and s[i].isdigit():\n"
                "            val = val * 10 + int(s[i])\n"
                "            i += 1\n"
                "        val *= sign\n"
                "        if val > INT_MAX: return INT_MAX\n"
                "        if val < INT_MIN: return INT_MIN\n"
                "        return val\n"
            ),
            'cpp': (
                "#include <string>\n"
                "#include <climits>\n"
                "#include <cctype>\n"
                "using namespace std;\n\n"
                "class Solution {\n"
                "public:\n"
                "    int myAtoi(string s) {\n"
                "        int i = 0, n = s.size();\n"
                "        while (i < n && s[i] == ' ') i++;\n"
                "        if (i == n) return 0;\n"
                "        int sign = 1;\n"
                "        if (s[i] == '+') { i++; }\n"
                "        else if (s[i] == '-') { sign = -1; i++; }\n"
                "        long long val = 0;\n"
                "        while (i < n && isdigit(s[i])) {\n"
                "            val = val * 10 + (s[i] - '0');\n"
                "            if (sign == 1 && val > INT_MAX) return INT_MAX;\n"
                "            if (sign == -1 && -val < INT_MIN) return INT_MIN;\n"
                "            i++;\n"
                "        }\n"
                "        return (int)(sign * val);\n"
                "    }\n"
                "};\n"
            )
        }
        Solution.objects.update_or_create(
            problem=p,
            defaults={
                'question_number': 8,
                'title': 'String to Integer (atoi)',
                'description': p.description,
                'code': sol_codes['python'],
                'code_by_language': sol_codes,
                'language': 'python',
                'explanation': (
                    "### Direct Parsing with Clamp\n\n"
                    "1. Strip leading spaces.\n"
                    "2. Check for optional `+` or `-` sign.\n"
                    "3. Parse subsequent digits until non-digit.\n"
                    "4. Clamp within 32-bit signed integer bounds `[-2^31, 2^31 - 1]`."
                ),
                'time_complexity': 'O(N)',
                'space_complexity': 'O(1)',
                'fetch_failed': False,
            }
        )

    def seed_utf8_validation(self):
        p, _ = Problem.objects.get_or_create(
            question_number=393,
            defaults={
                'title': 'UTF-8 Validation',
                'slug': 'utf-8-validation',
                'difficulty': 'Medium',
                'leetcode_id': 393,
            }
        )
        p.title = 'UTF-8 Validation'
        p.difficulty = 'Medium'
        p.execution_mode = 'FUNCTION'
        p.function_name = 'validUtf8'
        p.description = (
            "Given an integer array `data` representing the data, return `true` if it is a valid "
            "**UTF-8** encoding, or `false` otherwise.\n\n"
            "A character in UTF8 can be from **1 to 4 bytes** long, subjected to the following rules:\n\n"
            "1. For a 1-byte character, the first bit is a `0`, followed by its Unicode code.\n"
            "2. For an n-bytes character, the first n bits are all `1`s, the n + 1 bit is `0`, followed by n - 1 bytes with the most significant 2 bits being `10`.\n\n"
            "Only the least significant 8 bits of each integer are used to store the data."
        )
        p.examples = [
            {
                'input': 'data = [197,130,1]',
                'output': 'true',
                'explanation': 'The octets represent the sequence: 11000101 10000010 00000001. Valid 2-byte char followed by 1-byte char.'
            },
            {
                'input': 'data = [235,140,4]',
                'output': 'false',
                'explanation': 'The octets represent: 11101011 10001100 00000100. 1110 indicates 3-byte char, but 3rd octet starts with 00.'
            }
        ]
        p.constraints = [
            '1 <= data.length <= 2 * 10^4',
            '0 <= data[i] <= 255'
        ]
        p.save()

        TestCase.objects.filter(problem=p).delete()
        test_cases = [
            (False, '[197, 130, 1]', 'true', 1),
            (False, '[235, 140, 4]', 'false', 2),
            (True, '[0]', 'true', 3),
            (True, '[240, 162, 138, 147]', 'true', 4),
            (True, '[250]', 'false', 5),
            (True, '[248, 130, 130, 130]', 'false', 6),
            (True, '[145]', 'false', 7),
        ]
        for is_hidden, in_txt, out_txt, ord_num in test_cases:
            TestCase.objects.create(
                problem=p,
                is_hidden=is_hidden,
                input_text=in_txt,
                expected_output=out_txt,
                order=ord_num,
            )

        py_starter = (
            "class Solution:\n"
            "    def validUtf8(self, data: list[int]) -> bool:\n"
            "        # Write your solution here\n"
            "        pass\n"
        )
        py_harness = (
            "if __name__ == '__main__':\n"
            "    import sys, json\n"
            "    raw = sys.stdin.read().strip()\n"
            "    if raw:\n"
            "        data = json.loads(raw)\n"
            "        sol = Solution()\n"
            "        res = sol.validUtf8(data)\n"
            "        print('true' if res else 'false')\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='python',
            defaults={'starter_code': py_starter, 'harness_code': py_harness}
        )

        cpp_starter = (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "class Solution {\n"
            "public:\n"
            "    bool validUtf8(vector<int>& data) {\n"
            "        // Write your solution here\n"
            "        return false;\n"
            "    }\n"
            "};\n"
        )
        cpp_harness = (
            "#ifndef MAIN_DEFINED\n"
            "#include <iostream>\n"
            "#include <string>\n"
            "#include <sstream>\n"
            "#include <vector>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    string line;\n"
            "    if (!getline(cin, line)) return 0;\n"
            "    for (char &c : line) { if (c == '[' || c == ']' || c == ',') c = ' '; }\n"
            "    stringstream ss(line);\n"
            "    vector<int> data;\n"
            "    int v;\n"
            "    while (ss >> v) data.push_back(v);\n"
            "    Solution sol;\n"
            "    bool res = sol.validUtf8(data);\n"
            "    cout << (res ? \"true\" : \"false\") << endl;\n"
            "    return 0;\n"
            "}\n"
            "#endif\n"
        )
        LanguageTemplate.objects.update_or_create(
            problem=p, language='cpp',
            defaults={'starter_code': cpp_starter, 'harness_code': cpp_harness}
        )

        # Editorial Solution
        sol_codes = {
            'python': (
                "class Solution:\n"
                "    def validUtf8(self, data: list[int]) -> bool:\n"
                "        n_bytes = 0\n"
                "        mask1 = 1 << 7\n"
                "        mask2 = 1 << 6\n"
                "        for num in data:\n"
                "            mask = 1 << 7\n"
                "            if n_bytes == 0:\n"
                "                while mask & num:\n"
                "                    n_bytes += 1\n"
                "                    mask = mask >> 1\n"
                "                if n_bytes == 0: continue\n"
                "                if n_bytes == 1 or n_bytes > 4: return False\n"
                "            else:\n"
                "                if not (num & mask1 and not (num & mask2)): return False\n"
                "            n_bytes -= 1\n"
                "        return n_bytes == 0\n"
            )
        }
        Solution.objects.update_or_create(
            problem=p,
            defaults={
                'question_number': 393,
                'title': 'UTF-8 Validation',
                'description': p.description,
                'code': sol_codes['python'],
                'code_by_language': sol_codes,
                'language': 'python',
                'explanation': (
                    "### Bitmask Count Approach\n\n"
                    "For each byte in `data`:\n"
                    "1. If `n_bytes == 0`, count the number of leading 1s.\n"
                    "   - If 0 leading 1s: valid 1-byte ASCII character.\n"
                    "   - If 1 leading 1 or > 4 leading 1s: invalid UTF-8 header.\n"
                    "   - Otherwise: `n_bytes` is the number of continuation bytes remaining.\n"
                    "2. If `n_bytes > 0`, check that the byte begins with binary `10`.\n"
                    "3. Return `True` if `n_bytes == 0` after processing all bytes."
                ),
                'time_complexity': 'O(N)',
                'space_complexity': 'O(1)',
                'fetch_failed': False,
            }
        )
