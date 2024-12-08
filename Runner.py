import subprocess
import sys


def run_program():
    # Step 1: Run the external program e.exe and capture its output
    e_process = subprocess.Popen(
        ["R6 Dissect/r6-dissect.exe", sys.argv[1]],  # Adjust arguments as needed
        stdout=subprocess.PIPE,               # Capture stdout from e.exe
        stderr=subprocess.PIPE                # Capture stderr from e.exe
    )

    p_process = subprocess.Popen(
        ["python", "Caller.py"],  # Running your Python program
        stdin=e_process.stdout,  # Pipe e.exe's stdout to p.py's stdin
        stdout=subprocess.PIPE,  # Capture the output from p.py
        stderr=subprocess.PIPE  # Optionally capture stderr
    )

    e_process.stdout.close()

    p_output, p_error = p_process.communicate()

    if p_process.returncode != 0:
        print(f"Error occurred in p.py: {p_error.decode('utf-8')}")
    else:
        print(p_output.decode('utf-8'))


if __name__ == "__main__":
    run_program()