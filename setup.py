from setuptools import setup, find_packages

setup(
    name="testthread",
    version="0.4.0",
    packages=find_packages(),
    install_requires=["requests"],
    author="Eugene Dayne Mawuli",
    author_email="",
    description="pytest for AI agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/eugene001dayne/test-thread",
    license="Apache 2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
    python_requires=">=3.7",
)