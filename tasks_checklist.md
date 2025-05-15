# SELF-TEST SCENARIOS (TASKS CHECKLIST)
# This checklist tracks the implementation of self-test scenarios as specified in NOTES.md

+- Test to assess the ability to replace folder and file names in a directory tree of depth=10
+- Test to assess the ability to search and replace strings in files with GB18030 charset encoding
+- Test to assess the ability to replace a string with its replacement according to the replacement map
+- Test to assess the ability to leave intact the occurrences of the string that are not included in the replacement map
+- Test to assess the ability to find in text files multiple lines with the string occurrences
+- Test to assess the ability to create an entry for a transaction in the json file for each line of a file containing the string occurrences
+- Test to assess the ability to create an entry for a transaction in the json file for each file name containing the string occurrences
+- Test to assess the ability to create an entry for a transaction in the json file for each folder name containing the string occurrences
+- Test the ability to execute an entry for a transaction in the json file for each line of a file containing the string occurrences
+- Test the ability to execute an entry for a transaction in the json file for each file name containing the string occurrences
+- Test the ability to execute an entry for a transaction in the json file for each folder name containing the string occurrences
+- Test the ability to update the json field of the STATE of a transaction in realtime in an atomic and secure way
+- Test the ability to compare the first search and building the planned_transaction.json file with the second search that builds the planned_transaction_validation.json file, to ensure deterministic results
+- Test the ability to resume the job from a json file with an incomplete number of transactions added, and resume the SEARCH phase
+- Test the ability to resume the job from a json file with only a partial number of transactions have been marked with the COMPLETED value in the STATUS field, and to resume executing the remaining PLANNED or IN_PROGRESS transactions.
+- Test the ability to retry transactions executions that were marked with STATE = ERROR, and correctly determine if to try again, ask the user for sudo/permissions or to stop the job and exit with an error message.
+- Test the ability to find the search and replace the string inside files > 10MB using the line-by-line approach to reduce memory usage
+- Test the ability of the script to correctly parse the replacement_mapping.json file according to the parsing rules I told you before.
+- Test the ability of the script to make changes like a surgeon, only replacing the strings in the replacement_mapping.json configuration file and nothing else, leaving everything else exactly as was before, including: encoding, line endings, trailing chars, control characters, diacritics, malformed chars, illegal chars, corrupt chars, mixed encoding lines, spaces and invisible chars, etc. Everything must be identical and untouched except those occurrences matching the replacement map provided by the user. Do various tests about this, to consider all test cases.
+- Test to assess the fact that files that have not been found containing (in the name or content) strings that matches the replacement map are always left intact.
+- test the ability to detect and ignore symlinks (and not rename them) if the option `--ignore-symlinks` is used in the launch command.
