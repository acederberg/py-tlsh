"""My objective here is publish something suitable from this because it is
FUCKING IMPOSSIBLE to find a reasonable, working, maintained fuzzy hash library
and I am finding it to be incredibly frustrating to find anything working.

My goal is to compute hashes and compare them using levenshtein distance to
determine to what extent website content has changed.

# Notes About

Somebody made [a pr](https://github.com/trendmicro/tlsh/pull/133) with a pure python implementation.
This would appear to be a nearly literal translation of [the source implementation]( https://github.com/trendmicro/tlsh/blob/master/src/tlsh_impl.cpp).

There are a few resources to give context about what is happening here. This is
getting rather arcane and academic, however I should probably do this since 
finding a python fuzzy hashing tool is a pain in the ass.

1. [Definition](https://documents.trendmicro.com/assets/wp/wp-locality-sensitive-hash.pdf)
2. https://tlsh.org/papersDir/COINS_2020_camera_ready.pdf
3. [Papers](https://tlsh.org/papers.html)


# OG Notes

By default, 3 Bytes checksum and 32 Bytes (data/file-contents) is being used.
if checksum is same for 2 hashes, high probability that file is same, it may not be so useful in case of smaller strings !!!
by default EFF_BUCKETS = 128 (each correspond to 2 bits), which would mean 32 bytes hash.
Can try to change the EFF_BUCKETS to a higher (256) or lower value (64/32), depending upon the application user would want to use a HASH.
"""

import math

import typer

# NOTE: This array is hard coded directly into the C++ module. While users could probably
#       provide their own ``V_TABLE``, this is required for users to get the same result.

# fmt: off
V_TABLE = bytearray( [ 1, 87, 49, 12, 176, 178, 102, 166, 121, 193, 6, 84, 249, 230, 44, 163, 14, 197, 213, 181, 161, 85, 218, 80, 64, 239, 24, 226, 236, 142, 38, 200, 110, 177, 104, 103, 141, 253, 255, 50, 77, 101, 81, 18, 45, 96, 31, 222, 25, 107, 190, 70, 86, 237, 240, 34, 72, 242, 20, 214, 244, 227, 149, 235, 97, 234, 57, 22, 60, 250, 82, 175, 208, 5, 127, 199, 111, 62, 135, 248, 174, 169, 211, 58, 66, 154, 106, 195, 245, 171, 17, 187, 182, 179, 0, 243, 132, 56, 148, 75, 128, 133, 158, 100, 130, 126, 91, 13, 153, 246, 216, 219, 119, 68, 223, 78, 83, 88, 201, 99, 122, 11, 92, 32, 136, 114, 52, 10, 138, 30, 48, 183, 156, 35, 61, 26, 143, 74, 251, 94, 129, 162, 63, 152, 170, 7, 115, 167, 241, 206, 3, 150, 55, 59, 151, 220, 90, 53, 23, 131, 125, 173, 15, 238, 79, 95, 89, 16, 105, 137, 225, 224, 217, 160, 37, 123, 118, 73, 2, 157, 46, 116, 9, 145, 134, 228, 207, 212, 202, 215, 69, 229, 27, 188, 67, 124, 168, 252, 42, 4, 29, 108, 21, 247, 19, 205, 39, 203, 233, 40, 186, 147, 198, 192, 155, 33, 164, 191, 98, 204, 165, 180, 117, 76, 140, 36, 210, 172, 41, 54, 159, 8, 185, 232, 113, 196, 231, 47, 146, 120, 51, 65, 28, 144, 254, 221, 93, 189, 194, 139, 112, 43, 71, 109, 184, 209, ])
# fmt: on


LOG_1_5 = 0.4054651
LOG_1_3 = 0.26236426
LOG_1_1 = 0.095310180


# def mod_diff(x: int, y: int, R: int):
#     # difference conditioned on R aka range
#
#     dleft = 0
#     dright = 0
#     if y > x:
#         dleft = y - x
#         dright = x + R - y
#     else:
#         dleft = x - y
#         dright = y + R - x
#
#     if dleft > dright:
#         return dright
#     else:
#         return dlelft
#

##############################
# COnfiguration
#######################

SLIDING_WND_SIZE = 5
RNG_SIZE = SLIDING_WND_SIZE

TLSH_CHECKSUM_LEN = 1
BUCKETS = 256
EFF_BUCKETS = 128
assert EFF_BUCKETS % 8 == 0
CODE_SIZE = (
    EFF_BUCKETS * 2
) // 8  # EFF_BUCKETS(DEFAULT = 128) * 2 bits = 32 bytes = 64 hex characters. Each bucket is being represented using 2 bits. (00, 01, 10, 11)
TLSH_STRING_LEN = (CODE_SIZE + 3) * 2  # default = (32 + 3 )
RANGE_LVALUE = 256
RANGE_QRATIO = 16


class Uint32Array:
    # for now modelling it with standard int, if doesn't work, we would use numpy.
    def __init__(self, size: int) -> None:
        self.data = [int(0) for _ in range(size)]

    def __setitem__(self, key: int, value: int):
        self.data[key] = value

    def __getitem__(self, key: int):
        return self.data[key]

    def __str__(self):
        return str(self.data)

    def __len__(self):
        return len(self.data)


class Uint8Array:
    def __init__(self, size: int) -> None:
        self.data = bytearray([0 for _ in range(size)])

    def __setitem__(self, key: int, value: int):
        self.data[key] = value

    def __getitem__(self, key: int):
        return self.data[key]

    def __str__(self):
        return str(self.data)

    def __len__(self):
        return len(self.data)

    def to_hex(self, length: int | None = None) -> str:

        # generates a hex representation
        if length is None:
            data_length = len(self)
        else:
            data_length = len(self)

        s = self.data[:data_length].hex()
        assert len(s) == 2 * (data_length)
        return s

    def from_hex(self, val) -> bytearray:
        """

        # OG Comments

        NOTE: str is expected to be a result of something like to_hex
        resulting bytearray would have length of len(str) // 2.

        return bytearray([0 for i in range(32)])
        """

        assert len(val) % 2 == 0

        result = bytearray()
        for i in range(len(val) // 2):
            x = val[2 * i : 2 * i + 2]
            result.append(int(x, base=16))
        return result


class Buffer(object):
    def __init__(self, size: int) -> None:
        self.bucket_copy = Uint32Array(size=size)

    def swap_uint(self, x: int, y: int):
        int_tmp = self.bucket_copy[x]
        self.bucket_copy[x] = self.bucket_copy[y]
        self.bucket_copy[y] = int_tmp

    def partition(self, left, right):
        if left == right:
            return left
        if left + 1 == right:
            if self.bucket_copy[left] > self.bucket_copy[right]:
                self.swap_uint(left, right)
            return left

        ret = left
        pivot = (left + right) >> 1

        val = self.bucket_copy[pivot]

        self.bucket_copy[pivot] = self.bucket_copy[right]
        self.bucket_copy[right] = val

        for i in range(left, right):
            if self.bucket_copy[i] < val:
                self.swap_uint(ret, i)
                ret += 1

        self.bucket_copy[right] = self.bucket_copy[ret]
        self.bucket_copy[ret] = val

        return ret


def setQLo(Q: int, x: int) -> int:
    return (Q & 0xF0) | (x & 0x0F)


def setQHi(Q: int, x: int) -> int:
    return (Q & 0x0F) | ((x & 0x0F) << 4)


def getQHi(Q: int) -> int:
    return (Q & 0xF0) >> 4


def getQLo(Q: int) -> int:
    return Q & 0x0F


class Tlsh(object):
    checksum: Uint8Array
    slide_window: Uint8Array
    a_bucket: Uint32Array
    data_len: int
    tmp_code: Uint8Array
    Q: int

    def __init__(self) -> None:
        self.checksum = Uint8Array(size=TLSH_CHECKSUM_LEN)  # TO check
        self.slide_window = Uint8Array(
            size=SLIDING_WND_SIZE
        )  # sliding window size, used to scan the string.
        self.a_bucket = Uint32Array(size=BUCKETS)
        self.data_len = 0
        self.tmp_code = Uint8Array(size=CODE_SIZE)
        self.Lvalue = 0
        self.Q = 0
        self.lsh_code = ""
        self.lsh_code_valid = False

        self.q0 = 0  # lowest level  0b00
        self.q1 = None
        self.q2 = None
        self.q3 = None  # highest level 0b11

    @staticmethod
    def random(i: int):
        return (i + RNG_SIZE) % RNG_SIZE

    @staticmethod
    def create_lvalue(len: int):
        i = 0
        if len <= 656:
            i = math.floor(math.log(len) / LOG_1_5)
        elif len <= 3199:
            i = math.floor(math.log(len) / LOG_1_3 - 8.72777)
        else:
            i = math.floor(math.log(len) / LOG_1_1 - 62.5472)

        return i & 0xFF

    @staticmethod
    def b_mapping(salt, i, j, k) -> int:
        """This is the [first step described in [1]](https://documents.trendmicro.com/assets/wp/wp-locality-sensitive-hash.pdf).

        # OG Notes

        To map the trigrams to buckets. Based on the PEARSON algorithm.
        """

        h = 0
        h = V_TABLE[h ^ salt]
        h = V_TABLE[h ^ i]
        h = V_TABLE[h ^ j]
        h = V_TABLE[h ^ k]
        return h

    @staticmethod
    def swap_byte(i: int):
        byte = 0
        byte = ((i & 0xF0) >> 4) & 0x0F
        byte |= ((i & 0x0F) << 4) & 0xF0
        return byte

    def update(self, data: str, length=None):
        # length may not be None, if we want to override.
        data_length = length if length is not None else len(data)
        data_array = [ord(data[i]) for i in range(data_length)]
        if any(map(lambda code: code >= 255, data_array)):
            raise ValueError
        elif data_length != len(data):
            raise ValueError

        j = self.data_len % RNG_SIZE  # [0, siding window size)
        fed_len = self.data_len

        # slide over the data, and keep mapping to buckets.
        for i in range(data_length):
            self.slide_window[j] = data_array[i]

            if fed_len >= 4:
                j_1 = self.random(j - 1)
                j_2 = self.random(j - 2)
                j_3 = self.random(j - 3)
                j_4 = self.random(j - 4)

                for k in range(0, TLSH_CHECKSUM_LEN):
                    if k == 0:
                        self.checksum[k] = self.b_mapping(
                            salt=0,
                            i=self.slide_window[j],
                            j=self.slide_window[j_1],
                            k=self.checksum[k],
                        )
                        # print("CHECKSUM: {}".format(self.checksum[k]))
                    else:  # TODO: understand how if 1 is supposed to TLSH_CHECKSUM_LEN,
                        self.checksum[k] = self.b_mapping(
                            salt=self.checksum[k - 1],
                            i=self.slide_window[j],
                            j=self.slide_window[j_1],
                            k=self.checksum[k],
                        )

                    right = self.b_mapping(
                        2,
                        self.slide_window[j],
                        self.slide_window[j_1],
                        self.slide_window[j_2],
                    )
                    right = self.b_mapping(
                        2,
                        self.slide_window[j],
                        self.slide_window[j_1],
                        self.slide_window[j_2],
                    )
                    right = self.b_mapping(
                        2,
                        self.slide_window[j],
                        self.slide_window[j_1],
                        self.slide_window[j_2],
                    )

                    self.a_bucket[right] += 1  # increase the bucket count.
                    right = self.b_mapping(
                        3,
                        self.slide_window[j],
                        self.slide_window[j_1],
                        self.slide_window[j_3],
                    )
                    self.a_bucket[right] += 1
                    right = self.b_mapping(
                        5,
                        self.slide_window[j],
                        self.slide_window[j_2],
                        self.slide_window[j_3],
                    )
                    self.a_bucket[right] += 1
                    right = self.b_mapping(
                        7,
                        self.slide_window[j],
                        self.slide_window[j_2],
                        self.slide_window[j_4],
                    )
                    self.a_bucket[right] += 1
                    right = self.b_mapping(
                        11,
                        self.slide_window[j],
                        self.slide_window[j_1],
                        self.slide_window[j_4],
                    )
                    self.a_bucket[right] += 1
                    right = self.b_mapping(
                        13,
                        self.slide_window[j],
                        self.slide_window[j_3],
                        self.slide_window[j_4],
                    )
                    self.a_bucket[right] += 1

            fed_len += 1
            j = self.random(j + 1)

        self.data_len += data_length

    def find_quartiles(self):
        "updates the self.q1, self.q2, self.q3 fields. based on the stats for the bytes/data."

        buf = Buffer(size=EFF_BUCKETS)
        shortcut_left = Uint32Array(size=EFF_BUCKETS)
        shortcut_right = Uint32Array(size=EFF_BUCKETS)
        spl = 0
        spr = 0
        p1 = EFF_BUCKETS // 4 - 1
        p2 = EFF_BUCKETS // 2 - 1
        p3 = EFF_BUCKETS - (EFF_BUCKETS // 4) - 1
        end = EFF_BUCKETS - 1

        for i in range(0, end + 1):
            buf.bucket_copy[i] = self.a_bucket[i]

        left = 0
        right = end
        while True:
            ret = buf.partition(left, right)
            if ret > p2:
                right = ret - 1
                shortcut_right[spr] = ret
                spr += 1
            elif ret < p2:
                left = ret + 1
                shortcut_left[spl] = ret
                spl += 1
            else:
                self.q2 = buf.bucket_copy[p2]
                break

        shortcut_left[spl] = p2 - 1
        shortcut_right[spr] = p2 + 1

        # finding q1
        i = 0
        left = 0
        for i in range(0, spl + 1):
            right = shortcut_left[i]
            if right > p1:
                while True:
                    ret = buf.partition(left, right)
                    if ret > p1:
                        right = ret - 1
                    elif ret < p1:
                        left = ret + 1
                    else:
                        self.q1 = buf.bucket_copy[p1]
                        break

            elif right < p1:
                left = right
            else:
                self.q1 = buf.bucket_copy[p1]
                break

        # finding q3:
        right = end
        for i in range(0, spr + 1):
            left = shortcut_left[i]
            if left < p3:
                while True:
                    ret = buf.partition(left, right)
                    if ret > p3:
                        right = ret - 1
                    elif ret < p3:
                        left = ret + 1
                    else:
                        self.q3 = buf.bucket_copy[p3]
                        break
                break
            elif left > p3:
                right = left
            else:
                self.q3 = buf.bucket_copy[p3]
                break

    def final(self, data=None, length=None):

        if data is not None:
            self.update(data=data, length=length)

        assert self.data_len >= 256, "Length too small.."
        self.find_quartiles()  # find quartiles for provided data.

        assert self.q1 is not None
        assert self.q2 is not None
        assert self.q3 is not None

        # count the number of non-zero buckets.
        nonzero = 0
        for i in range(0, CODE_SIZE):
            for j in range(0, 4):
                if self.a_bucket[4 * i + j] > 0:
                    nonzero += 1
        assert nonzero > 4 * (
            CODE_SIZE // 2
        ), "Not enough variation to fill more than 50 percent buckets."

        for i in range(0, CODE_SIZE):
            h = 0
            for j in range(0, 4):
                k = self.a_bucket[4 * i + j]
                if self.q3 < k:
                    h += 3 << (j * 2)
                elif self.q2 < k:
                    h += 2 << (j * 2)
                elif self.q1 < k:
                    h += 1 << (j * 2)

            self.tmp_code[i] = h

        self.Lvalue = self.create_lvalue(self.data_len)
        self.Q = setQLo(self.Q, int(((self.q1 * 100) / self.q3) % 16))
        self.Q = setQHi(self.Q, int(((self.q2 * 100) / self.q3) % 16))
        self.lsh_code_valid = True

    def hash(self) -> str:
        assert self.lsh_code_valid is True

        tmp_checksum = Uint8Array(size=TLSH_CHECKSUM_LEN)
        tmp_Lvalue = 0
        tmp_Q = 0
        tmp_code = Uint8Array(CODE_SIZE)

        for k in range(0, TLSH_CHECKSUM_LEN):
            tmp_checksum[k] = self.swap_byte(self.checksum[k])

        tmp_Lvalue = self.swap_byte(self.Lvalue)
        tmp_Q = self.swap_byte(self.Q)

        for i in range(0, CODE_SIZE):
            tmp_code[i] = self.tmp_code[CODE_SIZE - 1 - i]

        self.lsh_code = tmp_checksum.to_hex(TLSH_CHECKSUM_LEN)  # +1

        tmpArray = Uint8Array(size=1)
        tmpArray[0] = tmp_Lvalue
        self.lsh_code += tmpArray.to_hex(1)  # +1

        tmpArray[0] = tmp_Q
        self.lsh_code += tmpArray.to_hex(1)  # +1
        self.lsh_code += tmp_code.to_hex(CODE_SIZE)  # +32
        return self.lsh_code  # 35 bytes. (70 hex characters)

    @classmethod
    def compute_hash(cls, value) -> str:
        self = cls()
        self.update(value)
        self.final()
        return self.hash()


# calculate distance b/w two Tlsh objects.
# def h_distance(diff_table: list[Uint8Array], length: int, x: int, y: int):
#     diff = 0
#     for i in range(0, length):
#         diff += diff_table[x[i]][y[i]]
#     return diff
#
#
# def totalDiff(diff_table: list[Uint8Array], a: Tlsh, b: Tlsh, len_diff: bool = False):
#     if a == b:
#         return 0
#
#     diff = 0
#
#     # in case want to include the file-length information in total distance.
#     if len_diff:
#         ldiff = mod_diff(a.Lvalue, b.Lvalue, RANGE_LVALUE)
#         if ldiff == 0:
#             diff = 0
#         elif ldiff == 1:
#             diff = 1
#         else:
#             diff += ldiff * 12  # read paper to know the significance of 12.
#
#     q1diff = mod_diff(getQLo(a.Q), getQLo(b.Q), RANGE_QRATIO)
#     if q1diff <= 1:
#         diff += q1diff
#     else:
#         diff += (q1diff - 1) * 12
#
#     q2diff = mod_diff(getQHi(a.Q), getQHi(b.Q), RANGE_QRATIO)
#     if q2diff <= 1:
#         diff += q2diff
#     else:
#         diff += (q2diff - 1) * 12
#
#     for k in range(0, TLSH_CHECKSUM_LEN):
#         if a.checksum[k] != b.checksum[k]:
#             diff += 1
#             break
#
#     diff += h_distance(diff_table, CODE_SIZE, a.tmp_code, b.tmp_code)
#
#     return diff
#
#
# def generateTable() -> list[Uint8Array]:
#     arraySize = 256
#     result = [Uint8Array(size=arraySize) for _ in range(arraySize)]
#
#     for i in range(0, arraySize):
#         for j in range(0, arraySize):
#             x = i
#             y = j
#             diff = 0
#
#             d = abs((x % 4) - (y % 4))
#             diff += int(d == 3) * 6 + int(d != 3) * d  # equivalent to (d == 3 ? 6:d)
#             x = math.floor(x / 4)
#             y = math.floor(y / 4)
#
#             d = abs((x % 4) - (y % 4))
#             diff += int(d == 3) * 6 + int(d != 3) * d  # equivalent to (d == 3 ? 6:d)
#             x = math.floor(x / 4)
#             y = math.floor(y / 4)
#
#             d = abs((x % 4) - (y % 4))
#             diff += int(d == 3) * 6 + int(d != 3) * d  # equivalent to (d == 3 ? 6:d)
#             x = math.floor(x / 4)
#             y = math.floor(y / 4)
#
#             d = abs((x % 4) - (y % 4))
#             diff += int(d == 3) * 6 + int(d != 3) * d  # equivalent to (d == 3 ? 6:d)
#
#             result[i][j] = diff
#
#     return result
#
#
# bit_pairs_diff_table = generateTable()


