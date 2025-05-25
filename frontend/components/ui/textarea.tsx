import React from "react";
export const Textarea = React.forwardRef(({ ...props }: any, ref) => <textarea ref={ref} {...props} />);
Textarea.displayName = "Textarea";
