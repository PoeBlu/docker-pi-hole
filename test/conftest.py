import pytest
import testinfra

DEBUG = []

check_output = testinfra.get_backend(
    "local://"
).get_module("Command").check_output

def DockerGeneric(request, args, image, cmd):
    assert 'docker' in check_output('id'), "Are you in the docker group?"
    if 'diginc/pi-hole' in image:
       args += " -e PYTEST=\"True\""
    docker_run = "docker run -d {} {} {}".format(args, image, cmd)
    docker_id = check_output(docker_run)

    def teardown():
        check_output("docker rm -f %s", docker_id)
    request.addfinalizer(teardown)

    docker_container = testinfra.get_backend("docker://" + docker_id)
    docker_container.id = docker_id
    return docker_container

@pytest.fixture
def Docker(request, args, image, cmd):
    ''' One-off Docker container run '''
    return DockerGeneric(request, args, image, cmd)

@pytest.fixture(scope='session')
def DockerPersist(request, persist_args, persist_image, persist_cmd, Dig):
    ''' Persistent Docker container for multiple tests '''
    persistent_container = DockerGeneric(request, persist_args, persist_image, persist_cmd)
    ''' attach a dig conatiner for lookups '''
    persistent_container.dig = Dig(persistent_container.id)
    return persistent_container

@pytest.fixture()
def args(request):
    return '-e ServerIP="192.168.100.2"'

@pytest.fixture(params=['alpine', 'debian'])
def tag(request):
    return request.param

@pytest.fixture
@pytest.mark.parametrize('tag,webserver', [ ( 'alpine', 'nginx' ), ( 'debian', 'lighttpd' ) ])
def webserver(request, tag):
    return webserver

@pytest.fixture()
def image(request, tag):
    return 'diginc/pi-hole:{}'.format(tag)

@pytest.fixture()
def cmd(request):
    return '/start.sh'

@pytest.fixture(scope='session')
def persist_args(request):
    return '-e ServerIP="192.168.100.2"'

@pytest.fixture(scope='session', params=['alpine', 'debian'])
def persist_tag(request):
    return request.param

@pytest.fixture(scope='session')
def persist_webserver(request, persist_tag):
    web_dict = { 'alpine': 'nginx', 'debian': 'lighttpd' }
    return web_dict[persist_tag]

@pytest.fixture(scope='session')
def persist_image(request, persist_tag):
    return 'diginc/pi-hole:{}'.format(persist_tag)

@pytest.fixture(scope='session')
def persist_cmd(request):
    return '/start.sh'

@pytest.fixture
def Slow():
    """
    Run a slow check, check if the state is correct for `timeout` seconds.
    """
    import time
    def slow(check, timeout=5):
        timeout_at = time.time() + timeout
        while True:
            try:
                assert check()
            except AssertionError, e:
                if time.time() < timeout_at:
                    time.sleep(1)
                else:
                    raise e
            else:
                return
    return slow

@pytest.fixture(scope='session')
def Dig(request):
    ''' separate container to link to pi-hole and perform lookups '''
    ''' a docker pull is faster than running an install of dnsutils '''
    def dig(docker_id):
        args  = '--link {}:pihole'.format(docker_id)
        image = 'azukiapp/dig'
        cmd   = 'tail -f /dev/null'
        dig_container = DockerGeneric(request, args, image, cmd)
        return dig_container
    return dig

