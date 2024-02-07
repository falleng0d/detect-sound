# Detect Sound

Python application that listens to audio input and performs actions based on the volume level. It includes a cooldown decorator and throttling logic to prevent the callback from being executed too frequently.

## Setting up venv

To set up a virtual environment for the project, follow these steps:

1. Ensure that you have Python installed on your system.
2. Navigate to the project directory in your terminal.
3. Run the following command to create a virtual environment:

```bash
python -m venv venv
```

4. Activate the virtual environment:

On Windows:
```bash
venv\Scripts\activate
```

On macOS and Linux:
```bash
source venv/bin/activate
```

5. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running application

To run the application, make sure you are in the project directory and the virtual environment is activated. Then execute:

```bash
python main.py
```

## Linting

To lint the code, ensure that you have installed the required development dependencies. You can use `ruff` for linting:

```bash
ruff .
```

To automatically fix linting errors, run:

```bash
ruff . --fix
```
