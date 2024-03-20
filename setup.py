from setuptools import setup

with open("README.md", "r") as fh:
    readme_long_description = fh.read()

setup(
    name='coder-sms-register',
    version='0.1.0-alpha1',
    description="coder-sms-register is a dockerized application that allows users to create logins and temporary passwords for a Coder server via SMS using Twilio. The intended use case is grantig access to Coder to leverage pre-configured templates designed to run code-server (VS Code in the browser) in during a hands-on classroom coding session. The Coder server allows students to learn a coding concept without having to install anything or configure their environment. They can code in the browser with dependencies and packages already installed.",
    long_description=readme_long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/shinyshoes404/coder-sms-register',
    author='shinyshoes',
    author_email='shinyshoes404@protonmail.com',
    license='MIT License',
    packages=['coder_sms_register'],
    package_dir={'':'src'},
    entry_points = { 'console_scripts' : ['start-coder-sms-reg=coder_sms_register.entrypoint:main']},
    
    install_requires=[
        'requests', 'sqlalchemy', 'flask', 'flask_cors', 'bcrypt', 'randomname', 'redis>=5.0.0rc2'
    ],

    extras_require={
        # To install requirements for dev work use 'pip install -e .[dev]' 
        'dev': ['coverage', 'mock']
    },

    python_requires = '>=3.11',

    classifiers=[
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.11'
    ],
)
