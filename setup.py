from setuptools import setup, find_packages

setup(
    name='spotipy_gato365',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pandas',
        'dotenv',
    ],
    author='Olivia Kurani, Mia Hodges, Adam Del Rio, Immanuel Williams',
    author_email='Olivia Email, Mia Email, AdamDelRio8523@gmail.com, Williams Email',
    description='A Python package utilizing API calls from the Spotify Web API for data science purposes',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/okurani/spotifypy_gato365',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
