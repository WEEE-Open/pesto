import json

# noinspection PyPackageRequirements
import pytest

from basilico import CommandRunner


def _remove_partn(lsblk):
    for device in lsblk["blockdevices"]:
        del device["partn"]


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt_basic(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/sda",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/sda1",
             "partn": 1,
             "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
          },{
             "path": "/dev/sda2",
             "partn": 2,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)
    expected = ("/dev/sda2", 2)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt_lots_of_partitions(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/sda",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/sda1",
             "partn": 1,
             "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
          },{
             "path": "/dev/sda2",
             "partn": 2,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda3",
             "partn": 3,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda4",
             "partn": 4,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda5",
             "partn": 5,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda6",
             "partn": 6,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda7",
             "partn": 7,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda8",
             "partn": 8,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda9",
             "partn": 9,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda10",
             "partn": 10,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/sda11",
             "partn": 11,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)
    expected = ("/dev/sda11", 11)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt_no_linux(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/sda",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/sdb1",
             "partn": 1,
             "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
          },{
             "path": "/dev/sdb2",
             "partn": 2,
             "parttype": "e3c9e316-0b5c-4db8-817d-f92df00215ae"
          },{
             "path": "/dev/sdb3",
             "partn": 3,
             "parttype": "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    # Windows partitions, nothing to do
    expected = (None, None)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/loop0",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/loop0p1",
             "partn": 1,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/loop0p2",
             "partn": 2,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/loop0p3",
             "partn": 3,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/loop0p4",
             "partn": 4,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)
    expected = ("/dev/loop0p4", 4)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_dont_trust_the_names(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/cool_drive",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/asd1",
             "partn": 1,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/bsd2",
             "partn": 2,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/csd999",
             "partn": 3,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/that_partition",
             "partn": 4,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)
    expected = ("/dev/that_partition", 4)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_dont_trust_the_names_2(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/cool_drive",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/asd1",
             "partn": 1,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/bsd2",
             "partn": 2,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/csd999",
             "partn": 3,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/that_partition",
             "partn": 4,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de5"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)
    expected = ("/dev/csd999", 3)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt_with_other_type(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/loop0",
             "partn": null,
             "parttype": null
          },{
             "path": "/dev/loop0p1",
             "partn": 1,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/loop0p2",
             "partn": 2,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/loop0p3",
             "partn": 3,
             "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
          },{
             "path": "/dev/loop0p4",
             "partn": 4,
             "parttype": "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    # Partition 4 is NTFS, not a Linux partition
    expected = ("/dev/loop0p3", 3)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt_empty(fallback):
    lsblk = json.loads(
        """
    {
       "blockdevices": [
          {
             "path": "/dev/sda",
             "partn": null,
             "parttype": null
          }
       ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    expected = (None, None)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_gpt_emptier(fallback):
    lsblk = json.loads(
        """
    {
        "blockdevices": [
        ]
    }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    expected = (None, None)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_mbr(fallback):
    lsblk = json.loads(
        """
        {
           "blockdevices": [
              {
                 "path": "/dev/loop0",
                 "partn": null,
                 "parttype": null
              },{
                 "path": "/dev/loop0p1",
                 "partn": 1,
                 "parttype": "0x83"
              },{
                 "path": "/dev/loop0p2",
                 "partn": 2,
                 "parttype": "0x6"
              },{
                 "path": "/dev/loop0p3",
                 "partn": 3,
                 "parttype": "0x83"
              }
           ]
        }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    expected = ("/dev/loop0p3", 3)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_mbr_not_last(fallback):
    lsblk = json.loads(
        """
        {
           "blockdevices": [
              {
                 "path": "/dev/loop0",
                 "partn": null,
                 "parttype": null
              },{
                 "path": "/dev/loop0p1",
                 "partn": 1,
                 "parttype": "0x83"
              },{
                 "path": "/dev/loop0p2",
                 "partn": 2,
                 "parttype": "0x6"
              },{
                 "path": "/dev/loop0p3",
                 "partn": 3,
                 "parttype": "0x8e"
              }
           ]
        }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    expected = ("/dev/loop0p1", 1)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_mbr_none(fallback):
    lsblk = json.loads(
        """
        {
           "blockdevices": [
              {
                 "path": "/dev/sdz0",
                 "partn": null,
                 "parttype": null
              },{
                 "path": "/dev/sdz1",
                 "partn": 1,
                 "parttype": "0xab"
              },{
                 "path": "/dev/sdz2",
                 "partn": 2,
                 "parttype": "0x6"
              },{
                 "path": "/dev/sdz3",
                 "partn": 3,
                 "parttype": "0x8e"
              }
           ]
         }
    """
    )
    if fallback:
        _remove_partn(lsblk)

    expected = (None, None)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected


@pytest.mark.parametrize("fallback", [False, True])
def test_get_last_linux_partition_path_and_number_from_lsblk_parttype_null(fallback):
    lsblk = json.loads(
        """
      {
         "blockdevices": [
            {
               "path": "/dev/sdz",
               "partn": null,
               "parttype": null
            },{
               "path": "/dev/sdz1",
               "partn": null,
               "parttype": null
            },{
               "path": "/dev/sdz2",
               "partn": 2,
               "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
            },{
               "path": "/dev/sdz3",
               "partn": 3,
               "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4"
            }
         ]
      }
      """
    )
    if fallback:
        _remove_partn(lsblk)

    expected = ("/dev/sdz3", 3)

    result = CommandRunner._get_last_linux_partition_path_and_number_from_lsblk(lsblk)

    # Assert that the result matches the expected output
    assert result == expected
