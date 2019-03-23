"""Present commands in lgit program."""
from os import environ, _exit, unlink, listdir
from os.path import exists, isfile, isdir, abspath

from functions import (make_directory, create_file, read_file,
                       copy_file_to_another, format_mtime, get_files_skip_lgit,
                       hashing_sha1_file, get_timestamp_of_current_time,
                       get_readable_date)


def execute_lgit_init():
    """Initialize version control in the current directory."""

    def _create_lgit_folders():
        """Create directories in .lgit structure."""
        lgit_folders = [
            '.lgit', '.lgit/objects', '.lgit/commits', '.lgit/snapshots'
        ]
        for folder in lgit_folders:
            make_directory(folder)

    def _create_lgit_files():
        """Create files in .lgit structure."""
        lgit_files = ['.lgit/index', '.lgit/config']
        for file in lgit_files:
            create_file(file)

    def _init_config():
        """Initialize the name of the author in the file config."""
        with open('.lgit/config', 'w') as config:
            config.write(environ['LOGNAME'])

    if exists('.lgit'):
        print("Git repository already initialized.")
    else:
        print("Initialized empty Git repository in %s/" % abspath('.lgit'))
    _create_lgit_folders()
    _create_lgit_files()
    _init_config()


def execute_lgit_add(args):
    """Add file contents to the index."""

    def _add_file_to_lgit_database(file, hash_value):
        """Store a copy of the file contents in the lgit database."""
        dir_path = '.lgit/objects/{}/'.format(hash_value[:2])
        make_directory(dir_path)
        copy_file_to_another(file, dir_path + hash_value[2:])

    def _update_index(file, hash_value):
        """Update the file information in the index file."""
        timestamp = format_mtime(file)
        with open('.lgit/index', 'rb+') as index:
            content_index = index.readlines()
            index.seek(0)
            added = False
            for line in content_index:
                if line.endswith((file + '\n').encode()):
                    index.write(timestamp.encode())
                    index.seek(42, 1)
                    index.write(hash_value.encode())
                    added = True
                else:
                    index.seek(len(line), 1)
            if not added:
                empty_hash = ' ' * 40
                line_index = '%s %s %s %s %s\n' % (
                    timestamp, hash_value, hash_value, empty_hash, file)
                index.write(line_index.encode())

    file_paths = []
    if '.' in args.files or '*' in args.files:
        file_paths = get_files_skip_lgit()
    else:
        for path in args.files:
            if isfile(path):
                file_paths.append(path)
            else:
                file_paths.extend(get_files_skip_lgit(path))

    for path in file_paths:
        sha1_value = hashing_sha1_file(path)
        _add_file_to_lgit_database(path, sha1_value)
        _update_index(path, sha1_value)


def execute_lgit_rm(args):
    """Remove a file from the working directory and the index."""

    def _remove_file_index(a_file):
        """Remove the information of the tracked a_file.

        Args:
            a_file: The tracked file.

        Returns:
            True/False: if a_file exist in the index file.

        """
        with open('.lgit/index', 'r+') as index:
            contents = index.readlines()
            had_file = False
            for line in contents:
                if line.endswith(a_file + '\n'):
                    contents.remove(line)
                    had_file = True
            index.truncate(0)
            index.write(''.join(contents))
        return had_file

    for file in args.files:
        if isdir(file):
            print("fatal: not removing '%s' recursively" % file)
            _exit(1)
        if exists(file):
            # If the file exists in the index file:
            # hash_value = hashing_sha1_file(file)
            # directory = '.lgit/object/' + hash_value[:2]
            # file_data = '.lgit/object/' + hash_value[2:]
            if _remove_file_index(file):
                unlink(file)
                # unlink(file_data)
                # try:
                #     rmdir(directory)
                # except OSError:
                #     pass
            else:
                print("fatal: pathspec '%s' did not match any files" % file)
                _exit(1)
        else:
            print("fatal: pathspec '%s' did not match any files" % file)
            _exit(1)


def config_lgit(args):
    """Set a user for authoring the commits."""
    with open('.lgit/config', 'w') as config:
        config.write(args.author + '\n')


def execute_lgit_commit(args):
    """Create a commit with the changes currently staged."""
    timestamp_now, ms_timestamp_now = get_timestamp_of_current_time()

    def _create_commit_object(message):
        """Create the commit object when commit the changes."""

        # Get the author name for the commits:
        author = read_file('.lgit/config').strip('\n')
        # If the config file is empty:
        if not author:
            print('''***Please tell me who you are.
            
            Run
            
            ./lgit.py config --author "Author Name"
            
            to set a user for authoring the commits.''')

        with open('.lgit/commits/%s' % ms_timestamp_now, 'w') as commit:
            # Write file in the commits directory:
            commit.write('%s\n%s\n\n%s\n\n' % (author, timestamp_now, message))

    def _update_index_and_snapshot():
        """Update the index file and create snapshots."""

        with open('.lgit/index', 'rb+') as index, open(
                '.lgit/snapshots/%s' % ms_timestamp_now, 'ab+') as snapshot:
            content_index = index.readlines()
            index.seek(0)
            for line in content_index:
                hash_value = line[56:96]
                file_path = line[138:]
                snapshot.write(hash_value + b' ' + file_path)
                index.seek(97, 1)
                index.write(hash_value)
                index.seek(len(line) - 137, 1)

    _create_commit_object(args.m)
    _update_index_and_snapshot()


def display_lgit_status(args):
    """Show the working tree status."""

    def _print_status_header():
        """Print the header of the status."""
        print('On branch master')
        # If the command commit has been never called:
        if not listdir('.lgit/commits'):
            print('\nNo commits yet\n')

    def _report_changes_to_be_committed(files):
        """Print information about changes to be committed."""
        print('Changes to be committed:')
        print('  (use "./lgit.py reset HEAD ..." to unstage)\n')
        for file in files:
            print('\tmodified:', file)
        print()

    def _report_changes_not_staged_for_commit(files):
        """Print information about changes not staged for commit."""
        print('Changes not staged for commit:')
        print('  (use "./lgit.py add ..." to update what will be committed)')
        print(
            '  (use "./lgit.py checkout -- ..." to discard changes in working directory)\n'
        )
        for file in files:
            print('\tmodified:', file)
        print(
            '\nno changes added to commit (use "./lgit.py add and/or "./lgit.py commit -a")'
        )

    def _report_untracked_files(files):
        """Report the untracked files when call the status command.

        Args:
            files: The files that are present in the working in the working directory,
                but have never been lgit add'ed.

        """

        print('Untracked files:')
        print(
            '  (use "./lgit.py add ..." to include in what will be committed)\n'
        )
        for file in files:
            print('\t' + file)
        print()
        # print('nothing added to commit but untracked files present
        # (use "./lgit.py add" to track)')

    def _update_index(file):
        """Update the index of the file in the working directory."""
        content_index = read_file('.lgit/index').split('\n')
        hash_value = hashing_sha1_file(file)
        timestamp, _ = get_timestamp_of_current_time()
        with open('.lgit/index', 'rb+') as index:
            current_line = None
            for line in content_index:
                if line[138:] == file:
                    current_line = '%s %s %s' % (timestamp, hash_value,
                                                 line[56:])
                    index.write((timestamp + ' ' + hash_value).encode())
                    break
                else:
                    index.seek(len(line) + 1, 1)
        return current_line

    def _classify_files():
        """Classify files in the working directory."""
        list_files = get_files_skip_lgit()
        untracked_files = []
        files_to_be_committed = []
        files_not_staged_for_commit = []
        for file in list_files:
            info_file = _update_index(file)
            if info_file:
                if info_file[56:96] != info_file[15:55]:
                    files_not_staged_for_commit.append(file)
                if info_file[97:137] != info_file[56:96]:
                    files_to_be_committed.append(file)
            else:
                untracked_files.append(file)
        return untracked_files, files_to_be_committed, files_not_staged_for_commit

    _print_status_header()
    untracked, to_be_committed, not_staged_for_commit = _classify_files()
    if to_be_committed:
        _report_changes_to_be_committed(to_be_committed)
    if not_staged_for_commit:
        _report_changes_not_staged_for_commit(not_staged_for_commit)
    if untracked:
        _report_untracked_files(untracked)


def list_lgit_files(args):
    """Show information about files in the index and the working tree."""

    content_index = read_file('.lgit/index').split('\n')
    list_files = []
    for line in content_index:
        list_files.append(line[138:])
    for file in sorted(list_files):
        if file != '':
            print(file)


def show_lgit_log(args):
    """Show the commit history."""

    def _display_commit(file):
        """Display each commit."""
        content = read_file('.lgit/commits/%s' % file).split('\n')
        print('commit ' + file)
        print('Author: ' + content[0])
        print('Date: ' + get_readable_date(file), end='\n\n')
        print('    %s\n' % content[3])

    list_commits = listdir('.lgit/commits')
    list_commits.sort(reverse=True)
    for commit in list_commits:
        _display_commit(commit)
