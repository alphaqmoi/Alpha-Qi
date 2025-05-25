import React, { useState } from "react";
export const Tabs = ({ children }: any) => <div>{children}</div>;
export const TabsList = ({ children }: any) => <div>{children}</div>;
export const TabsTrigger = ({ children, ...props }: any) => <button {...props}>{children}</button>;
export const TabsContent = ({ children }: any) => <div>{children}</div>;
