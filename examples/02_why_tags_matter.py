"""See how a lost boundary tag produces a wrong answer with no error message.

Run with: python examples/02_why_tags_matter.py

The problem is heat flow on a unit square with a known exact solution, so the true error can
be measured. Losing the "top" tag doesn't crash anything: the solver simply insulates that
side, because that is the method's default where no condition is set.
"""

from meshpreflight.validation import demonstrate_lost_tag

result = demonstrate_lost_tag(level=4)

print(f"Error with all boundary tags:   {result['error_with_all_tags']:.6f}")
print(f"Error without the 'top' tag:    {result['error_without_top_tag']:.6f}")
print(f"That is {result['times_worse']:.0f} times worse, and the solver raised no error.")
print(f"\nmeshpreflight reports: {', '.join(result['preflight_codes'])}")
