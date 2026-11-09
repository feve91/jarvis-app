Run yes | buildozer android debug
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.11.18/x64/bin/buildozer", line 6, in <module>
    sys.exit(main())
             ^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.18/x64/lib/python3.11/site-packages/buildozer/scripts/client.py", line 13, in main
    Buildozer().run_command(sys.argv[1:])
    ^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.18/x64/lib/python3.11/site-packages/buildozer/__init__.py", line 127, in __init__
    self.config.read(filename, "utf-8")
  File "/opt/hostedtoolcache/Python/3.11.18/x64/lib/python3.11/configparser.py", line 719, in read
    self._read(fp, filename)
  File "/opt/hostedtoolcache/Python/3.11.18/x64/lib/python3.11/configparser.py", line 1095, in _read
    raise DuplicateSectionError(sectname, fpname,
configparser.DuplicateSectionError: While reading from 'buildozer.spec' [line 46]: section 'buildozer' already exists
yes: standard output: Broken pipe
Error: Process completed with exit code 1.
