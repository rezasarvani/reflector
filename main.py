import asyncio
import aiohttp
import urllib.parse
import argparse
import random
import time
from typing import Dict, List, Set
import sys
import uuid
from colorama import init, Fore, Style
import json


from openai import verify_ssl_certs

init()

def load_user_agents():
    file_handle = open("useragents.json", "r")
    user_agents = json.load(file_handle)
    file_handle.close()
    return user_agents

USER_AGENTS = load_user_agents()

class URLParameterTester:
    def __init__(self, url: str, random_agent: bool, concurrent: int, delay: bool, delay_range: str, exclude: str, debug: bool, include: str, timeout: int):
        self.url = url
        self.random_agent = random_agent
        self.delay = delay
        self.delay_range = delay_range
        self.exclude = exclude.split(',') if exclude else []
        self.concurrent = concurrent
        self.timeout = timeout
        self.debug = debug
        self.include = include.split(",") if include else []
        self.test_chars = [
            '<',
            '>',
            '"',
            "'",
            '`',
            ';',
            '&',
            '=',
            '#',
            '%',
            '(',
            ')',
            '{',
            '}',
            '[',
            ']',
            '/',
            '\\',
            '*',
            '|'
        ]
        self.test_chars = self.test_chars + self.include
        self.headers = self._get_random_headers() if self.random_agent else {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        self.timeout = aiohttp.ClientTimeout(total=self.timeout)

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random headers to lower detection profile."""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': random.choice(['text/html', '*/*', 'application/json']),
            'Connection': 'keep-alive'
        }

    def extract_parameters(self) -> Dict[str, str]:
        """Extract all parameters from the URL."""
        try:
            parsed_url = urllib.parse.urlparse(self.url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            return {k: v[0] if v else "" for k, v in query_params.items()}
        except Exception as e:
            print(f"{Fore.RED}Error parsing URL: {e}{Style.RESET_ALL}")
            return {}

    async def test_reflection(self, session: aiohttp.ClientSession, param: str, original_value: str,
                              test_char: str) -> tuple:
        """Test a single character for reflection with a unique identifier."""
        unique_id = str(uuid.uuid4())[:10].replace("-", "")
        test_value = f"{original_value}{test_char}{unique_id}"
        modified_url = self._modify_url(param, test_value)
        expected_reflection = f"{test_char}{unique_id}"

        try:
            async with session.get(modified_url,
                                   headers=self.headers if not self.random_agent else self._get_random_headers(),
                                   timeout=self.timeout, ssl=False) as response:
                text = await response.text()
                if expected_reflection in text:
                    return (param, test_char, True)
                return (param, test_char, False)
        except Exception as e:
            return (param, test_char, f"Error: {str(e)}")

    def _modify_url(self, param: str, value: str) -> str:
        """Modify the URL with the test parameter value efficiently."""
        parsed_url = urllib.parse.urlparse(self.url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params[param] = value
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        return urllib.parse.urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))

    async def run_tests(self, param: str, original_value: str) -> Dict[str, List[str]]:
        """Run tests for a single parameter asynchronously."""
        results = {'reflected': [], 'not_reflected': [], 'errors': []}
        tasks = []

        async with aiohttp.ClientSession() as session:
            for test_char in self.test_chars:
                if test_char not in self.exclude:
                    tasks.append(self.test_reflection(session, param, original_value, test_char))

            semaphore = asyncio.Semaphore(self.concurrent)

            async def sem_task(task):
                async with semaphore:
                    if self.delay:
                        start_range, end_range = self.delay_range.split(",")
                        start_range, end_range = float(start_range), float(end_range)
                        await asyncio.sleep(random.uniform(start_range, end_range))
                    return await task

            responses = await asyncio.gather(*[sem_task(task) for task in tasks])

            for param, char, result in responses:
                if isinstance(result, bool):
                    if result:
                        results['reflected'].append(char)
                        if self.debug:
                            print(
                                f"{Fore.YELLOW}[+] '{char}' reflected unsanitized in response for parameter '{param}'{Style.RESET_ALL}")
                    else:
                        results['not_reflected'].append(char)
                else:
                    results['errors'].append(f"{char}: {result}")
                    print(f"{Fore.RED}[-] Error testing '{char}' for parameter '{param}': {result}{Style.RESET_ALL}")

        return results

    def analyze_url(self):
        """Main function to analyze the URL and test all parameters."""
        print(f"\n{Fore.BLUE}Analyzing URL: {self.url}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Low profile mode: {'Enabled' if self.random_agent else 'Disabled'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Concurrent requests: {self.concurrent}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Delay: {'Enabled' if self.delay else 'Disabled'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Delay Range: {self.delay_range}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Debug Message: {self.debug}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Exclude Characters: {', '.join(self.exclude) if self.exclude else '[NONE]'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Include Characters: {', '.join(self.include) if self.include else '[NONE]'}{Style.RESET_ALL}")
        print("=" * 50)

        params = self.extract_parameters()
        if not params:
            print(f"{Fore.RED} No parameters found in the URL!{Style.RESET_ALL}")
            return

        print(f"[*] Found parameters: {list(params.keys())}")
        print(f"{Fore.YELLOW}Testing parameter reflection...{Style.RESET_ALL}")

        loop = asyncio.get_event_loop()
        for param, original_value in params.items():
            print(f"{Fore.MAGENTA} Testing parameter: {param}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA} Original value: {original_value}{Style.RESET_ALL}")
            print("-" * 40)

            results = loop.run_until_complete(self.run_tests(param, original_value))

            if results['reflected']:
                print(
                    f"{Fore.GREEN}Reflected characters without sanitization (potential vulnerability):{Style.RESET_ALL}")
                for char in results['reflected']:
                    print(f"{Fore.GREEN}  - {char}{Style.RESET_ALL}")
            if results['not_reflected']:
                if self.debug:
                    print(f"{Fore.YELLOW}Non-reflected or sanitized characters:{Style.RESET_ALL}")
                    for char in results['not_reflected']:
                        print(f"{Fore.YELLOW}  - {char}{Style.RESET_ALL}")
            if results['errors']:
                print(f"{Fore.RED}Errors encountered:{Style.RESET_ALL}")
                for error in results['errors']:
                    print(f"{Fore.RED}  - {error}{Style.RESET_ALL}")
            print("=" * 50)


def parse_args():
    parser = argparse.ArgumentParser(description="URL Parameter Reflection Tester")
    parser.add_argument("url", help="Target URL to test (e.g., 'https://example.com?page=1&id=2')")
    parser.add_argument("--random-agent",
                        action="store_true",
                        default=True,
                        help="Enable random User-Agent for each request (default: true)")
    parser.add_argument("--delay",
                        action="store_true",
                        default=False,
                        help="Enable random delay between requests (default: false)")
    parser.add_argument("--delay-range",
                        type=str,
                        default="0.1,0.5",
                        help="Change the default random delay range (format: start,end | default: false)")
    parser.add_argument("--concurrent",
                        type=int,
                        default=5,
                        help="Number of concurrent requests (default: 5)")
    parser.add_argument("--timeout",
                        type=int,
                        default=5,
                        help="Maximum timeout for each request (default: 5)")
    parser.add_argument("--exclude",
                        type=str,
                        default=False,
                        help="Exclude list of characters from scanning (format: comma separated | default: None)")
    parser.add_argument("--include",
                        type=str,
                        default=False,
                        help="List of characters to append to default character list (format: comma separated | default: None)")
    parser.add_argument("--debug",
                        action="store_true",
                        default=False,
                        help="Show more information in output (default: False)")
    return parser.parse_args()


def main():
    args = parse_args()
    tester = URLParameterTester(args.url,
                                random_agent=args.random_agent,
                                concurrent=args.concurrent,
                                timeout=args.timeout,
                                delay=args.delay,
                                delay_range=args.delay_range,
                                debug=args.debug,
                                exclude=args.exclude,
                                include=args.include)
    tester.analyze_url()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass