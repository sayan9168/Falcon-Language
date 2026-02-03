from setuptools import setup

setup(
    name="falcon-lang",
    version="4.5.0",
    description="A secure, AI-native programming language for 2026.",
    author="Sayan",
    py_modules=["falcon_engine"],
    install_requires=[
        "google-generativeai",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "falcon=falcon_engine:main", # এটিই 'falcon' কমান্ড তৈরি করবে
        ],
    },
)
