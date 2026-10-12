import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { chatMarkdownComponents } from "./ChatPage";

describe("Markdown Sanitization and XSS Prevention (§11.10)", () => {
  it("strips executable <script> tags from rendered output", () => {
    const maliciousMarkdown = "Normal text before <script>alert('XSS-EXPLOIT')</script> and after.";
    const { container } = render(
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={chatMarkdownComponents}
      >
        {maliciousMarkdown}
      </ReactMarkdown>
    );

    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).not.toContain("<script");
    expect(container.innerHTML).not.toContain("</script>");
    expect(container.textContent).toContain("Normal text before");
    expect(container.textContent).toContain("and after.");
  });

  it("strips malicious inline onerror and onload event handlers", () => {
    const maliciousImg = "Image: <img src=\"nonexistent.png\" onerror=\"alert('PWNED')\" />";
    const { container } = render(
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={chatMarkdownComponents}
      >
        {maliciousImg}
      </ReactMarkdown>
    );

    const img = container.querySelector("img");
    if (img) {
      expect(img.getAttribute("onerror")).toBeNull();
    }
    expect(container.innerHTML).not.toContain("onerror");
    expect(container.innerHTML).not.toContain("alert('PWNED')");
  });

  it("strips dangerous <iframe> and <object> elements", () => {
    const maliciousIframe = "Preview: <iframe src=\"https://malicious-site.example/steal\"></iframe>";
    const { container } = render(
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={chatMarkdownComponents}
      >
        {maliciousIframe}
      </ReactMarkdown>
    );

    expect(container.querySelector("iframe")).toBeNull();
    expect(container.querySelector("object")).toBeNull();
  });

  it("disallows dangerous javascript: pseudo-protocol in markdown links", () => {
    const maliciousLink = "[Click to claim reward](javascript:alert(document.cookie))";
    const { container } = render(
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={chatMarkdownComponents}
      >
        {maliciousLink}
      </ReactMarkdown>
    );

    const link = container.querySelector("a");
    if (link) {
      expect(link.getAttribute("href")).not.toContain("javascript:");
    } else {
      expect(container.textContent).toContain("Click to claim reward");
    }
  });

  it("adds rel='noopener noreferrer nofollow' and target='_blank' to external links", () => {
    const externalLinkMarkdown = "Check our [Documentation](https://repogpt.local/docs) here.";
    const { container } = render(
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={chatMarkdownComponents}
      >
        {externalLinkMarkdown}
      </ReactMarkdown>
    );

    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("https://repogpt.local/docs");
    expect(link?.getAttribute("target")).toBe("_blank");
    expect(link?.getAttribute("rel")).toBe("noopener noreferrer nofollow");
  });

  it("keeps in-app relative links without external target or rel attributes", () => {
    const inAppLinkMarkdown = "Go back to [Repo Overview](/repos/123/overview).";
    const { container } = render(
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={chatMarkdownComponents}
      >
        {inAppLinkMarkdown}
      </ReactMarkdown>
    );

    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/repos/123/overview");
    expect(link?.getAttribute("target")).toBeNull();
    expect(link?.getAttribute("rel")).toBeNull();
  });
});
