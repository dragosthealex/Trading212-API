from setuptools import setup, find_packages

setup(
    name="trading212api",
    version="v0.2rc1",
    packages=find_packages(),
    install_requires=[
        'bs4',
        'pyyaml',
        'selenium',
        'pandas'
    ],
    include_package_data=True,
    package_data={'': ['*.ini', 'logs/*.ini', 'data/*_instruments.csv']},
    zip_safe=False,
    author="Alex Radu",
    author_email="dragosthealx@gmail.com",
    description="Package to interact with the broker service Trading212",
    license="MIT",
    keywords=("trading api broker automate selenium day trading cfd investment "
              "portfolio analysis management quantitative finance findev"),
    url="https://github.com/dragosthealex/Trading212-API",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: System :: Emulators'
    ]
)
