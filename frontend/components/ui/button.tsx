import React from "react";
export const Button = React.forwardRef(({ children, ...props }: any, ref) => (
  <button ref={ref} {...props}>{children}</button>
));
Button.displayName = "Button";
