# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/MartinPdeS/PyMieSimX/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                     |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| PyMieSimX/application/wsgi.py                            |        2 |        2 |        0 |        0 |      0.00% |       3-5 |
| PyMieSimX/gui/components/cards.py                        |       21 |       10 |        0 |        0 |     52.38% |16, 19-21, 24, 31-34, 37 |
| PyMieSimX/gui/interface.py                               |      332 |      234 |       78 |        2 |     24.39% |82, 86-115, 123-124, 134-140, 156-161, 180-221, 258-281, 298-339, 343-344, 348-349, 353-354, 358, 362, 382-394, 405-415, 443-462, 494-524, 534-548, 557-564, 581-585, 618-636, 647-665, 677-692, 701-704, 714-727, 742-748, 753, 758-763, 768-772, 780-781 |
| PyMieSimX/gui/layout.py                                  |       76 |       51 |       20 |        0 |     26.04% |27-87, 98, 182, 207, 250, 276-282, 287-357, 377-380, 388-391, 396-398 |
| PyMieSimX/gui/material\_catalog.py                       |       41 |       31 |       18 |        0 |     16.95% |38-57, 65-77, 82-88 |
| PyMieSimX/gui/pages/citation.py                          |        7 |        1 |        0 |        0 |     85.71% |        24 |
| PyMieSimX/gui/pages/documentation.py                     |        8 |        3 |        0 |        0 |     62.50% |10, 65, 69 |
| PyMieSimX/gui/pages/experiment/page.py                   |        8 |        2 |        0 |        0 |     75.00% |     15-16 |
| PyMieSimX/gui/pages/experiment/sections/configuration.py |       15 |        7 |        0 |        0 |     53.33% |11, 15, 19, 23-34 |
| PyMieSimX/gui/pages/field\_syntax.py                     |       15 |        8 |        0 |        0 |     46.67% |10, 50-51, 61-62, 69-70, 77 |
| PyMieSimX/gui/pages/home.py                              |       17 |        9 |        0 |        0 |     47.06% |11-12, 65-68, 73, 101, 121 |
| PyMieSimX/gui/pages/install\_local.py                    |       12 |        3 |        0 |        0 |     75.00% |16, 32, 37 |
| PyMieSimX/gui/pages/sellmeier.py                         |       10 |        6 |        2 |        0 |     33.33% |     11-32 |
| PyMieSimX/gui/pages/settings.py                          |       22 |       11 |        0 |        0 |     50.00% |13-16, 41-42, 46, 56, 79, 83, 87 |
| PyMieSimX/gui/pages/single/page.py                       |        6 |        1 |        0 |        0 |     83.33% |        13 |
| PyMieSimX/gui/pages/single/sections/representations.py   |        5 |        1 |        0 |        0 |     80.00% |         9 |
| PyMieSimX/gui/pages/single/sections/setup.py             |       10 |        3 |        0 |        0 |     70.00% |11, 15, 19 |
| PyMieSimX/gui/parsing.py                                 |       87 |       27 |       48 |       17 |     62.96% |16, 19, 24, 30, 34-40, 50, 53, 59-61, 71, 84-89, 97, 100, 103, 114, 119, 125, 129, 149 |
| PyMieSimX/gui/services.py                                |      375 |      222 |      120 |       11 |     37.98% |152-154, 162-245, 275-284, 342-348, 353-374, 379-478, 483-491, 503-\>505, 534, 546-\>545, 549-\>556, 556-\>560, 561, 573-577, 582-589, 594-625, 637-642, 673, 678, 683-700, 705-714, 732-735 |
| **TOTAL**                                                | **1095** |  **632** |  **286** |   **30** | **38.02%** |           |

2 files skipped due to complete coverage.


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/MartinPdeS/PyMieSimX/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/MartinPdeS/PyMieSimX/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/MartinPdeS/PyMieSimX/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/MartinPdeS/PyMieSimX/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FMartinPdeS%2FPyMieSimX%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/MartinPdeS/PyMieSimX/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.