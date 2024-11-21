# A Pure Python Fuzzy Hasher (for now)

**This is currently a work in progress.**

I needed a pure python fuzzy hasher. I have documents that I want to track the
differences in over time, and would like to use the fuzzy hashes to compare
their distance. However just about everything I could find had issues - many
of the projects had not been maintained in years had bad code packaged and
deployed to pypi. Eventually, I found ``TLSH``, and saw that [a pull request](https://github.com/trendmicro/tlsh/pull/133)
that contained a literal translation of ``TLSH`` in ``C``. I decided to use
this to write an idiomatic python implementation of ``TLSH``.

Of course, this is not as fast as the original ``TLSH``, but I do not need it
to be particularly fast. If you really need speed, I would recommend [the
original ``TLSH``](https://github.com/trendmicro/tlsh).

Eventually, I would like to move some of the implementation to ``C`` or ``Rust``.
However, I would rather not use the code from the original ``TLSH``.


