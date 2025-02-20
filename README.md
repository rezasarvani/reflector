## URL Parameter Reflection Tester
A Python script designed for bug bounty hunters and security researchers to test URL parameters for unsanitized reflection of special characters, which could indicate potential vulnerabilities like XSS or injection points. This tool uses asynchronous requests for efficiency, skips SSL verification for flexibility, and includes color-coded output for better readability.

## Features

* Asynchronous Requests: Uses asyncio and aiohttp for fast, concurrent testing.
* SSL Verification Disabled: Bypasses certificate checks to test servers with invalid/self-signed certificates.
* Color-Coded Output: Green for reflected characters, red for errors, yellow for non-reflected characters, and more.

## Customizable:
* Random User-Agents from a JSON file.
* Concurrent request limits.
* Optional random delays to lower detection profile.
* Exclude/include specific characters for testing.
* Debug mode for verbose output.

## Prerequisites
Python 3.7+

## Required libraries (install via pip):
```bash
pip install aiohttp colorama
```

Or you can use the requirements.txt file
```bash
pip install -r requirements.txt
```

## Installation
Clone or download this repository:
```bash
git clone <repository-url>
cd <repository-dir>
```

## Usage
Run the script with:
```bash
python main.py [options] <url>
```
You can get help using the following CLI switch
```bash
python main.py -h
```

## Todo
* Make it also check empty parameters in input URL (For example it must also check for *test2* query parameter within the https://target.com/main.php?test1=test1&test2=&test3=test3)

