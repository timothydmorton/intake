import os
import pytest
import shutil

from intake.source.cache import FileCache
import intake
here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def file_cache():
    return FileCache('csv', 
                     {'argkey': 'urlpath', 'regex': 'test/path', 'type': 'file'})


def test_ensure_cache_dir(file_cache):
    file_cache._ensure_cache_dir()
    assert os.path.exists(file_cache._cache_dir)

    file_cache.clear_all()
    shutil.rmtree(file_cache._cache_dir)

    with open(file_cache._cache_dir, 'w') as f:
        f.write('')
    
    with pytest.raises(Exception):
        file_cache._ensure_cache_dir()

    os.remove(file_cache._cache_dir)
    
    file_cache.clear_all()


def test_munge_path(file_cache):
    subdir = 'subdir'
    cache_path = file_cache._munge_path(subdir, 'test/path/foo.cvs')
    assert subdir in cache_path
    assert 'test/path' not in cache_path

    file_cache._spec['regex'] = 'https://example.com'
    cache_path = file_cache._munge_path(subdir, 'https://example.com/catalog.yml')
    assert subdir in cache_path
    assert file_cache._cache_dir in cache_path
    assert 'http' not in cache_path


def test_hash(file_cache):
    subdir = file_cache._hash('foo/bar.csv')

    import string
    # Checking for md5 hash
    assert all(c in string.hexdigits for c in subdir)

    file_cache._driver = 'bar'
    subdir_new = file_cache._hash('foo/bar.csv')
    assert subdir_new != subdir

    file_cache._driver = 'csv'
    subdir_new = file_cache._hash('foo/bar.csv')
    assert subdir_new == subdir

    file_cache._spec['regex'] = 'foo/bar'
    subdir_new = file_cache._hash('foo/bar.csv')
    assert subdir_new != subdir


def test_path(file_cache):
    urlpath = 'test/path/foo.csv'
    file_cache._spec['regex'] = 'test/path/'
    cache_path = file_cache._path(urlpath)

    assert file_cache._cache_dir in cache_path
    assert '//' not in cache_path[1:]
    file_cache.clear_all()


def test_path_no_match(file_cache):
    "No match should be a noop."
    urlpath = 'https://example.com/foo.csv'
    cache_path = file_cache._path(urlpath)
    assert urlpath == cache_path


def test_dir_cache(tmpdir):
    [os.makedirs(os.path.join(tmpdir, d)) for d in [
        'main', 'main/sub1', 'main/sub2']]
    for f in ['main/afile', 'main/sub1/subfile', 'main/sub2/subfile1',
              'main/sub2/subfile2']:
        fn = os.path.join(tmpdir, f)
        with open(fn, 'w') as fo:
            fo.write(f)
    fn = os.path.join(tmpdir, 'cached.yaml')
    shutil.copy2(os.path.join(here, 'cached.yaml'), fn)
    try:
        cat = intake.open_catalog(fn)
        s = cat.dirs()
        out = s.cache[0].load(s._urlpath, output=False)
        assert out[0] == os.path.join(tmpdir, s.cache[0]._path(s._urlpath))
        assert open(os.path.join(out[0], 'afile')).read() == 'main/afile'
    finally:
        shutil.rmtree(tmpdir)


def test_compressed_cache():
    cat = intake.open_catalog(os.path.join(here, 'cached.yaml'))
    s = cat.calvert()
    old = intake.config.conf['cache_download_progress']
    try:
        intake.config.conf['cache_download_progress'] = False
        df = s.read()
        assert len(df)
    finally:
        intake.config.conf['cache_download_progress'] = old
