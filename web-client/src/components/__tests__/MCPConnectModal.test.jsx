import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import MCPConnectModal from '../MCPConnectModal';

// ---------------------------------------------------------------------------
// Clipboard mock
// configurable: true so jsdom internals can redefine it without throwing
// ---------------------------------------------------------------------------
const writeTextMock = vi.fn().mockResolvedValue(undefined);

Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: writeTextMock },
    writable: true,
    configurable: true,
});

// import.meta.env is empty in Vitest — component falls back to these values
const FALLBACK_URL = 'https://your-ngrok-url.ngrok.io';
const MOCK_TOKEN = 'your-mcp-token';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const renderOpen = (onClose = vi.fn()) =>
    render(<MCPConnectModal isOpen={true} onClose={onClose} />);

const clickTab = (label) =>
    fireEvent.click(screen.getByRole('button', { name: new RegExp(label, 'i') }));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MCPConnectModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    // -----------------------------------------------------------------------
    // 1. Visibility
    // -----------------------------------------------------------------------
    describe('visibility', () => {
        it('renders nothing when isOpen is false', () => {
            render(<MCPConnectModal isOpen={false} onClose={vi.fn()} />);
            expect(screen.queryByText('Connect to Memora')).not.toBeInTheDocument();
        });

        it('renders the modal when isOpen is true', () => {
            renderOpen();
            expect(screen.getByText('Connect to Memora')).toBeInTheDocument();
        });

        it('shows the modal subtitle', () => {
            renderOpen();
            expect(
                screen.getByText('Add your MCP server to an external LLM client')
            ).toBeInTheDocument();
        });

        it('shows the MCP token notice banner', () => {
            renderOpen();
            expect(screen.getByText(/MCP Token required/i)).toBeInTheDocument();
        });

        it('shows a link to generate an MCP token from Profile', () => {
            renderOpen();
            expect(screen.getByText(/Profile → MCP Access Token/i)).toBeInTheDocument();
        });
    });

    // -----------------------------------------------------------------------
    // 2. Tab navigation
    // -----------------------------------------------------------------------
    describe('tab navigation', () => {
        it('renders all three tab buttons', () => {
            renderOpen();
            expect(screen.getByRole('button', { name: /ChatGPT/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Claude\.ai/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Claude Desktop/i })).toBeInTheDocument();
        });

        it('shows ChatGPT tab content by default', () => {
            renderOpen();
            expect(screen.getByText(/Streamable HTTP/i)).toBeInTheDocument();
        });

        it('switches to Claude.ai tab on click', () => {
            renderOpen();
            clickTab('Claude\\.ai');
            // /sse endpoint URL is only visible on the Claude.ai tab
            expect(screen.getByText(`${FALLBACK_URL}/sse`)).toBeInTheDocument();
        });

        it('switches to Claude Desktop tab on click', () => {
            renderOpen();
            clickTab('Claude Desktop');
            expect(screen.getByText(/claude_desktop_config\.json/i)).toBeInTheDocument();
        });

        it('switching back to ChatGPT tab shows /mcp URL again', () => {
            renderOpen();
            clickTab('Claude\\.ai');
            clickTab('ChatGPT');
            expect(screen.getByText(`${FALLBACK_URL}/mcp`)).toBeInTheDocument();
        });

        it('cycles through all three tabs without errors', () => {
            renderOpen();
            clickTab('Claude\\.ai');
            clickTab('Claude Desktop');
            clickTab('ChatGPT');
            expect(screen.getByText(`${FALLBACK_URL}/mcp`)).toBeInTheDocument();
        });
    });

    // -----------------------------------------------------------------------
    // 3. ChatGPT tab content
    // -----------------------------------------------------------------------
    describe('ChatGPT tab', () => {
        it('displays the /mcp endpoint URL', () => {
            renderOpen();
            expect(screen.getByText(`${FALLBACK_URL}/mcp`)).toBeInTheDocument();
        });

        it('displays the Authorization bearer header', () => {
            renderOpen();
            expect(
                screen.getByText(`Authorization: Bearer ${MOCK_TOKEN}`)
            ).toBeInTheDocument();
        });

        it('shows step referencing ChatGPT Settings → Beta Features', () => {
            renderOpen();
            expect(screen.getByText(/ChatGPT → Settings → Beta Features/i)).toBeInTheDocument();
        });

        it('shows step about adding MCP Server', () => {
            renderOpen();
            expect(screen.getByText(/Add MCP Server/i)).toBeInTheDocument();
        });

        it('shows step about Bearer Token authentication', () => {
            renderOpen();
            expect(screen.getByText(/Bearer Token/i)).toBeInTheDocument();
        });

        it('shows step about Memora context being injected', () => {
            renderOpen();
            expect(screen.getByText(/Memora context will be injected/i)).toBeInTheDocument();
        });
    });

    // -----------------------------------------------------------------------
    // 4. Claude.ai tab content
    // -----------------------------------------------------------------------
    describe('Claude.ai tab', () => {
        beforeEach(() => {
            renderOpen();
            clickTab('Claude\\.ai');
        });

        it('displays the /sse endpoint URL', () => {
            expect(screen.getByText(`${FALLBACK_URL}/sse`)).toBeInTheDocument();
        });

        it('displays the Authorization bearer header', () => {
            expect(
                screen.getByText(`Authorization: Bearer ${MOCK_TOKEN}`)
            ).toBeInTheDocument();
        });

        it('shows step referencing Claude.ai → Settings → Integrations', () => {
            expect(screen.getByText(/Claude\.ai → Settings → Integrations/i)).toBeInTheDocument();
        });

        it('shows step about adding a custom header', () => {
            expect(screen.getByText(/custom header/i)).toBeInTheDocument();
        });

        it('shows step about enriching every message', () => {
            expect(screen.getByText(/enrich every message/i)).toBeInTheDocument();
        });
    });

    // -----------------------------------------------------------------------
    // 5. Claude Desktop tab content
    // -----------------------------------------------------------------------
    describe('Claude Desktop tab', () => {
        beforeEach(() => {
            renderOpen();
            clickTab('Claude Desktop');
        });

        it('renders a <pre> block with the JSON config', () => {
            expect(document.querySelector('pre')).not.toBeNull();
        });

        it('JSON config contains the /sse URL', () => {
            const pre = document.querySelector('pre');
            expect(pre.textContent).toContain(`${FALLBACK_URL}/sse`);
        });

        it('JSON config contains the Authorization header value', () => {
            const pre = document.querySelector('pre');
            expect(pre.textContent).toContain(`Bearer ${MOCK_TOKEN}`);
        });

        it('JSON config block is valid JSON', () => {
            const pre = document.querySelector('pre');
            expect(() => JSON.parse(pre.textContent)).not.toThrow();
        });

        it('parsed JSON has the mcpServers.memora.url field', () => {
            const config = JSON.parse(document.querySelector('pre').textContent);
            expect(config).toHaveProperty('mcpServers.memora.url', `${FALLBACK_URL}/sse`);
        });

        it('parsed JSON has the mcpServers.memora.headers.Authorization field', () => {
            const config = JSON.parse(document.querySelector('pre').textContent);
            expect(config.mcpServers.memora.headers.Authorization).toBe(
                `Bearer ${MOCK_TOKEN}`
            );
        });

        it('shows a "Copy All" button', () => {
            expect(screen.getByRole('button', { name: /Copy All/i })).toBeInTheDocument();
        });

        it('shows step referencing Claude Desktop → Settings → Developer', () => {
            expect(
                screen.getByText(/Claude Desktop → Settings → Developer/i)
            ).toBeInTheDocument();
        });

        it('shows step about restarting Claude Desktop', () => {
            expect(screen.getByText(/restart Claude Desktop/i)).toBeInTheDocument();
        });

        it('shows step about the memora MCP tools panel', () => {
            expect(screen.getByText(/memora.*MCP tools panel/i)).toBeInTheDocument();
        });
    });

    // -----------------------------------------------------------------------
    // 6. Copy button behaviour
    // -----------------------------------------------------------------------
    describe('copy buttons', () => {
        it('calls clipboard.writeText with the /mcp URL when first Copy is clicked', async () => {
            renderOpen();
            const [firstCopy] = screen.getAllByRole('button', { name: /^Copy$/i });
            await act(async () => { fireEvent.click(firstCopy); });
            expect(writeTextMock).toHaveBeenCalledWith(`${FALLBACK_URL}/mcp`);
        });

        it('calls clipboard.writeText with the auth header when second Copy is clicked', async () => {
            renderOpen();
            const copyButtons = screen.getAllByRole('button', { name: /^Copy$/i });
            await act(async () => { fireEvent.click(copyButtons[1]); });
            expect(writeTextMock).toHaveBeenCalledWith(
                `Authorization: Bearer ${MOCK_TOKEN}`
            );
        });

        it('shows "Copied" label immediately after clicking Copy', async () => {
            renderOpen();
            const [firstCopy] = screen.getAllByRole('button', { name: /^Copy$/i });
            await act(async () => { fireEvent.click(firstCopy); });
            expect(screen.getAllByRole('button', { name: /Copied/i }).length).toBeGreaterThan(0);
        });

        it('reverts Copy button label back after 2 seconds', async () => {
            renderOpen();
            const [firstCopy] = screen.getAllByRole('button', { name: /^Copy$/i });
            await act(async () => { fireEvent.click(firstCopy); });
            // Advance timers inside act so React flushes the state update
            act(() => { vi.advanceTimersByTime(2100); });
            expect(screen.getAllByRole('button', { name: /^Copy$/i }).length).toBeGreaterThan(0);
        });

        it('Copy All writes the full JSON config to clipboard', async () => {
            renderOpen();
            clickTab('Claude Desktop');
            await act(async () => {
                fireEvent.click(screen.getByRole('button', { name: /Copy All/i }));
            });
            expect(writeTextMock).toHaveBeenCalledTimes(1);
            const written = writeTextMock.mock.calls[0][0];
            const parsed = JSON.parse(written);
            expect(parsed.mcpServers.memora.url).toBe(`${FALLBACK_URL}/sse`);
        });

        it('Copy All button shows "Copied!" after click', async () => {
            renderOpen();
            clickTab('Claude Desktop');
            await act(async () => {
                fireEvent.click(screen.getByRole('button', { name: /Copy All/i }));
            });
            expect(screen.getByRole('button', { name: /Copied!/i })).toBeInTheDocument();
        });

        it('Copy All button reverts after 2 seconds', async () => {
            renderOpen();
            clickTab('Claude Desktop');
            await act(async () => {
                fireEvent.click(screen.getByRole('button', { name: /Copy All/i }));
            });
            act(() => { vi.advanceTimersByTime(2100); });
            expect(screen.getByRole('button', { name: /Copy All/i })).toBeInTheDocument();
        });

        it('/sse URL is copied on Claude.ai tab', async () => {
            renderOpen();
            clickTab('Claude\\.ai');
            const [firstCopy] = screen.getAllByRole('button', { name: /^Copy$/i });
            await act(async () => { fireEvent.click(firstCopy); });
            expect(writeTextMock).toHaveBeenCalledWith(`${FALLBACK_URL}/sse`);
        });
    });

    // -----------------------------------------------------------------------
    // 7. Close / dismiss behaviour
    // -----------------------------------------------------------------------
    describe('close behaviour', () => {
        it('calls onClose when the footer Close button is clicked', () => {
            const onClose = vi.fn();
            render(<MCPConnectModal isOpen={true} onClose={onClose} />);
            fireEvent.click(screen.getByRole('button', { name: /^Close$/i }));
            expect(onClose).toHaveBeenCalledTimes(1);
        });

        it('calls onClose when the backdrop overlay is clicked', () => {
            const onClose = vi.fn();
            const { container } = render(<MCPConnectModal isOpen={true} onClose={onClose} />);
            fireEvent.click(container.firstChild); // outermost backdrop div
            expect(onClose).toHaveBeenCalledTimes(1);
        });

        it('does NOT call onClose when clicking inside the modal card', () => {
            const onClose = vi.fn();
            render(<MCPConnectModal isOpen={true} onClose={onClose} />);
            fireEvent.click(screen.getByText('Connect to Memora'));
            expect(onClose).not.toHaveBeenCalled();
        });
    });

    // -----------------------------------------------------------------------
    // 8. Footer
    // -----------------------------------------------------------------------
    describe('footer', () => {
        it('displays the MCP server base URL', () => {
            renderOpen();
            expect(screen.getByText(FALLBACK_URL)).toBeInTheDocument();
        });

        it('shows a pulsing status dot in the footer', () => {
            renderOpen();
            const footer = document.querySelector('.animate-pulse');
            expect(footer).not.toBeNull();
        });
    });

    // -----------------------------------------------------------------------
    // 9. Tab state isolation
    // -----------------------------------------------------------------------
    describe('tab state isolation', () => {
        it('switching tabs clears copy state from the previous tab', async () => {
            renderOpen();
            // Copy on ChatGPT tab
            const [firstCopy] = screen.getAllByRole('button', { name: /^Copy$/i });
            await act(async () => { fireEvent.click(firstCopy); });
            expect(screen.getAllByRole('button', { name: /Copied/i }).length).toBeGreaterThan(0);
            // Switch tab — new tab should not have Copied state
            clickTab('Claude\\.ai');
            expect(screen.queryByRole('button', { name: /Copied/i })).not.toBeInTheDocument();
        });

        it('Claude.ai and ChatGPT tabs show different endpoint paths', () => {
            renderOpen();
            expect(screen.getByText(`${FALLBACK_URL}/mcp`)).toBeInTheDocument();
            clickTab('Claude\\.ai');
            expect(screen.getByText(`${FALLBACK_URL}/sse`)).toBeInTheDocument();
        });
    });
});
