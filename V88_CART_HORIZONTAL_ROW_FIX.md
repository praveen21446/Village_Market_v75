# v88 Cart Quantity Horizontal Row Fix

On phone screens the cart quantity control is forced to render on one horizontal line:

`[ − ] [ quantity ] [ + ] kg`

A higher-specificity CSS rule overrides the older mobile table rule that forced every direct cell into `display:block`, which was causing the quantity control to stack vertically.
