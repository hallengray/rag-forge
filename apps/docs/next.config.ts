import nextra from "nextra";

const withNextra = nextra({
  search: { codeblocks: true },
  defaultShowCopyCode: true,
});

export default withNextra({
  reactStrictMode: true,
});
