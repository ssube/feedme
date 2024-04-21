import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="packit-llm",
    version="0.0.1",
    author="ssube",
    author_email="seansube@gmail.com",
    description="an LLM toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ssube/packit",
    keywords=[
        'llm',
    ],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)
