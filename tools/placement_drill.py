import json
import os
import random
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DRILLS_FILE = STORAGE_DIR / "memory" / "placement_drills.json"
DRILLS_FILE.parent.mkdir(parents=True, exist_ok=True)

QUESTIONS_BANK = [
    {
        "id": "ZOHO-01",
        "category": "DSA",
        "company": "Zoho Advanced Coding Round",
        "difficulty": "Medium",
        "topic": "Strings & Two Pointers",
        "title": "Run-Length String Expansion (e.g. a1b10)",
        "question": (
            "Write a program to give the following output for the given input:\n"
            "Input: a1b10\n"
            "Output: abbbbbbbbbb\n\n"
            "Input: b3c6d15\n"
            "Output: bbbccccccddddddddddddddd\n\n"
            "The number after each alphabet indicates how many times that character must be printed. "
            "Numbers can have multiple digits (e.g., 10, 15)."
        ),
        "hints": [
            "Traverse the string character by character.",
            "When encountering a letter, save it. While encountering digits, accumulate them to form the full multi-digit integer (e.g. num = num * 10 + (ch - '0')).",
            "When the next letter is hit or end of string, append the character 'num' times."
        ],
        "solution_java": """import java.util.Scanner;

public class ZohoStringExpansion {
    public static void main(String[] args) {
        String s = "a1b10";
        StringBuilder sb = new StringBuilder();
        int i = 0, n = s.length();
        
        while (i < n) {
            char ch = s.charAt(i++);
            int count = 0;
            while (i < n && Character.isDigit(s.charAt(i))) {
                count = count * 10 + (s.charAt(i++) - '0');
            }
            while (count-- > 0) {
                sb.append(ch);
            }
        }
        System.out.println("Result: " + sb.toString());
    }
}
// Time Complexity: O(Total characters in output)
// Space Complexity: O(Output Length)
""",
        "explanation": "Extract the character, parse consecutive digits into a number using Horner's rule (`val * 10 + digit`), then repeat appending."
    },
    {
        "id": "TCS-02",
        "category": "DSA",
        "company": "TCS Digital / TCS Prime",
        "difficulty": "Medium",
        "topic": "Two Pointers / Arrays",
        "title": "Container With Most Water",
        "question": (
            "Given an integer array height of length n. There are n vertical lines drawn such that the two endpoints "
            "of the ith line are (i, 0) and (i, height[i]).\n"
            "Find two lines that together with the x-axis form a container, such that the container contains the most water.\n\n"
            "Example:\nInput: height = [1,8,6,2,5,4,8,3,7]\nOutput: 49\nExplanation: Lines at index 1 and 8 (height 8 and 7) form area min(8,7) * (8 - 1) = 7 * 7 = 49."
        ),
        "hints": [
            "Use two pointers: left at 0, right at n-1.",
            "Current area = min(height[left], height[right]) * (right - left).",
            "Always move the pointer that has the smaller height inward."
        ],
        "solution_java": """public class MaxWater {
    public static int maxArea(int[] height) {
        int left = 0, right = height.length - 1;
        int max = 0;
        while (left < right) {
            int h = Math.min(height[left], height[right]);
            max = Math.max(max, h * (right - left));
            if (height[left] < height[right]) {
                left++;
            } else {
                right--;
            }
        }
        return max;
    }
}
// Time Complexity: O(N) single pass
// Space Complexity: O(1)
""",
        "explanation": "Greedy Two Pointers: Moving the taller side cannot increase the area because width decreases and height is bounded by the shorter line."
    },
    {
        "id": "INFY-03",
        "category": "DSA",
        "company": "Infosys Specialist Programmer",
        "difficulty": "Medium",
        "topic": "Sliding Window / HashMap",
        "title": "Longest Substring Without Repeating Characters",
        "question": (
            "Given a string s, find the length of the longest substring without duplicate characters.\n\n"
            "Example 1: s = 'abcabcbb' -> Output: 3 ('abc')\n"
            "Example 2: s = 'bbbbb' -> Output: 1 ('b')\n"
            "Example 3: s = 'pwwkew' -> Output: 3 ('wke')"
        ),
        "hints": [
            "Use a sliding window [left, right] and an int array of size 128 (or HashMap) storing the last seen index of each character.",
            "If character s[right] was seen inside current window, jump left = Math.max(left, lastSeen[char] + 1)."
        ],
        "solution_java": """import java.util.Arrays;

public class LongestUniqueSubstr {
    public static int lengthOfLongestSubstring(String s) {
        int[] last = new int[128];
        Arrays.fill(last, -1);
        int maxLen = 0, left = 0;
        for (int right = 0; right < s.length(); right++) {
            char c = s.charAt(right);
            if (last[c] >= left) {
                left = last[c] + 1;
            }
            last[c] = right;
            maxLen = Math.max(maxLen, right - left + 1);
        }
        return maxLen;
    }
}
// Time Complexity: O(N)
// Space Complexity: O(1) [fixed 128 ASCII array]
""",
        "explanation": "Optimal Sliding window with direct index lookup jumps the left pointer immediately without incremental inner loops."
    },
    {
        "id": "ZOHO-04",
        "category": "DSA",
        "company": "Zoho Round 2 & 3",
        "difficulty": "Hard",
        "topic": "Matrix / 2D Simulation",
        "title": "Spiral Matrix Printing Clockwise",
        "question": (
            "Given an m x n matrix, return all elements of the matrix in spiral order.\n\n"
            "Example:\nInput: matrix = [\n  [1, 2, 3],\n  [4, 5, 6],\n  [7, 8, 9]\n]\nOutput: [1, 2, 3, 6, 9, 8, 7, 4, 5]"
        ),
        "hints": [
            "Maintain 4 boundary pointers: top=0, bottom=m-1, left=0, right=n-1.",
            "Traverse left to right (top row), then increment top.",
            "Traverse top to bottom (right col), then decrement right.",
            "Check top <= bottom before traversing right to left, then decrement bottom.",
            "Check left <= right before traversing bottom to top, then increment left."
        ],
        "solution_java": """import java.util.*;

public class SpiralMatrix {
    public static List<Integer> spiralOrder(int[][] matrix) {
        List<Integer> res = new ArrayList<>();
        if (matrix == null || matrix.length == 0) return res;
        int top = 0, bottom = matrix.length - 1;
        int left = 0, right = matrix[0].length - 1;

        while (top <= bottom && left <= right) {
            for (int j = left; j <= right; j++) res.add(matrix[top][j]);
            top++;
            for (int i = top; i <= bottom; i++) res.add(matrix[i][right]);
            right--;
            if (top <= bottom) {
                for (int j = right; j >= left; j--) res.add(matrix[bottom][j]);
                bottom--;
            }
            if (left <= right) {
                for (int i = bottom; i >= top; i--) res.add(matrix[i][left]);
                left++;
            }
        }
        return res;
    }
}
""",
        "explanation": "Maintain tight loop boundaries and check remaining row/col invariants after shrinking each edge."
    },
    {
        "id": "APTI-01",
        "category": "Aptitude",
        "company": "TCS NQT / Cognizant GenC",
        "difficulty": "Easy-Medium",
        "topic": "Time and Work",
        "title": "A and B Alternating Work Days",
        "question": (
            "A can do a piece of work in 12 days and B can do it in 15 days.\n"
            "They work alternately, starting with A on the first day.\n"
            "In how many days will the entire work be completed?"
        ),
        "hints": [
            "Assume Total Work = LCM(12, 15) = 60 units.",
            "A's efficiency = 60/12 = 5 units/day.",
            "B's efficiency = 60/15 = 4 units/day.",
            "In 2 days (A + B), work done = 5 + 4 = 9 units."
        ],
        "solution_java": """Calculation:
1. Total Work = LCM(12, 15) = 60 units.
2. A's 1-day work = 60 / 12 = 5 units.
3. B's 1-day work = 60 / 15 = 4 units.
4. Work done in 2 days (1 cycle) = 5 + 4 = 9 units.
5. In 6 cycles (12 days), work done = 6 * 9 = 54 units.
6. Remaining work = 60 - 54 = 6 units.
7. On Day 13 (A's turn): A completes 5 units.
   Remaining work = 6 - 5 = 1 unit.
8. On Day 14 (B's turn): B takes (1 / 4) day.
Total Time = 12 + 1 + 1/4 = 13 (1/4) days or 13.25 days.
""",
        "explanation": "LCM method converts fractional work into whole integer units for instant mental calculation."
    },
    {
        "id": "APTI-02",
        "category": "Aptitude",
        "company": "Infosys / Wipro Turbo",
        "difficulty": "Medium",
        "topic": "Speed, Time & Distance",
        "title": "Two Trains Crossing in Opposite Directions",
        "question": (
            "Two trains of lengths 120m and 180m are running on parallel tracks in opposite directions.\n"
            "Their speeds are 42 km/hr and 30 km/hr respectively.\n"
            "Find the time taken by them to completely cross each other from the moment they meet."
        ),
        "hints": [
            "Total distance to cover = Sum of lengths of both trains.",
            "When moving in OPPOSITE directions, Relative Speed = Speed 1 + Speed 2.",
            "Convert Relative Speed from km/hr to m/s by multiplying by (5 / 18).",
            "Time = Distance / Relative Speed."
        ],
        "solution_java": """Calculation:
1. Total Distance = 120 + 180 = 300 meters.
2. Relative Speed = 42 + 30 = 72 km/hr.
3. Convert to m/s: 72 * (5 / 18) = 4 * 5 = 20 m/s.
4. Time taken = Distance / Speed = 300 / 20 = 15 seconds.

Answer: 15 seconds.
""",
        "explanation": "Opposite directions add speeds; same direction subtracts speeds. Always remember 5/18 conversion!"
    }
]

def get_daily_drill(category: str = "ALL") -> dict:
    """Returns a selected question for placement drill."""
    bank = QUESTIONS_BANK
    if category.upper() in ["DSA", "CODING"]:
        bank = [q for q in QUESTIONS_BANK if q["category"] == "DSA"]
    elif category.upper() in ["APTI", "APTITUDE"]:
        bank = [q for q in QUESTIONS_BANK if q["category"] == "Aptitude"]
    
    q = random.choice(bank)
    return q

def get_solution(qid: str) -> dict:
    """Fetches solution for a given question ID."""
    for q in QUESTIONS_BANK:
        if q["id"].lower() == qid.strip().lower():
            return q
    return None

def record_drill_progress(qid: str, status: str = "SOLVED"):
    data = {"history": [], "solved_count": 0}
    if DRILLS_FILE.exists():
        try:
            with open(DRILLS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    
    data["history"].append({
        "qid": qid,
        "timestamp": datetime.now().isoformat(),
        "status": status
    })
    data["solved_count"] = sum(1 for h in data["history"] if h.get("status") == "SOLVED")
    data["last_practiced"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    with open(DRILLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data

if __name__ == "__main__":
    q = get_daily_drill()
    print("Daily Drill Selected:")
    print(f"[{q['id']}] {q['title']} ({q['company']})")
    print(q['question'])
