from setuptools import setup, find_packages

setup(
    name="testthread",
    version="0.12.0",
    description="pytest for AI agents. Test, monitor, and catch behavioral drift.",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Eugene Dayne Mawuli",
    author_email="bitelance.team@gmail.com",
    url="https://github.com/eugene001dayne/test-thread",
    packages=find_packages(),
    install_requires=["httpx"],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)