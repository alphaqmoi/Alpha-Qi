import React from "react";
export const Select = ({ children, ...props }: any) => <select {...props}>{children}</select>;
export const SelectContent = ({ children }: any) => <>{children}</>;
export const SelectItem = ({ children, ...props }: any) => <option {...props}>{children}</option>;
export const SelectTrigger = ({ children, ...props }: any) => <div {...props}>{children}</div>;
export const SelectValue = ({ children }: any) => <>{children}</>;
