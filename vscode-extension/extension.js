const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const DIAGNOSTICS_COLLECTION = vscode.languages.createDiagnosticCollection('leakguard');

function getAnalyzerPath() {
    const config = vscode.workspace.getConfiguration('leakguard');
    const customPath = config.get('analyzerPath', '');
    if (customPath && fs.existsSync(customPath)) {
        return customPath;
    }
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (workspaceRoot) {
        const candidate = path.join(workspaceRoot, 'analyzer', 'checker.py');
        if (fs.existsSync(candidate)) {
            return path.join(workspaceRoot, 'analyzer');
        }
    }
    return null;
}

function getPythonPath() {
    return vscode.workspace.getConfiguration('leakguard').get('pythonPath', 'python');
}

function getSeverity() {
    const sev = vscode.workspace.getConfiguration('leakguard').get('severity', 'Warning');
    switch (sev) {
        case 'Error': return vscode.DiagnosticSeverity.Error;
        case 'Information': return vscode.DiagnosticSeverity.Information;
        default: return vscode.DiagnosticSeverity.Warning;
    }
}

function analyzeFile(filePath) {
    return new Promise((resolve, reject) => {
        const analyzerDir = getAnalyzerPath();
        if (!analyzerDir) {
            resolve([]);
            return;
        }

        const pythonPath = getPythonPath();
        const script = `
import sys, json
sys.path.insert(0, ${JSON.stringify(analyzerDir)})
from checker import analyze_file
result = analyze_file(${JSON.stringify(filePath)})
print(json.dumps(result))
`;

        const proc = spawn(pythonPath, ['-c', script], {
            cwd: analyzerDir,
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', (data) => { stdout += data.toString(); });
        proc.stderr.on('data', (data) => { stderr += data.toString(); });

        proc.on('close', (code) => {
            if (code !== 0 && !stdout) {
                resolve([]);
                return;
            }
            try {
                const results = JSON.parse(stdout.trim());
                resolve(results);
            } catch (e) {
                resolve([]);
            }
        });

        proc.on('error', () => resolve([]));
    });
}

async function scanDocument(document) {
    if (document.languageId !== 'python') return;

    const filePath = document.uri.fsPath;
    const leaks = await analyzeFile(filePath);

    const diagnostics = [];

    for (const leak of leaks) {
        const line = Math.max(0, (leak.line_number || 1) - 1);
        const range = new vscode.Range(
            new vscode.Position(line, 0),
            new vscode.Position(line, document.lineAt(line).text.length)
        );

        const severity = getSeverity();
        const isUncertain = leak.status === 'UNCERTAIN';

        const diag = new vscode.Diagnostic(
            range,
            `[LeakGuard] ${leak.resource_name}: ${leak.leak_type}${isUncertain ? ' (uncertain - needs review)' : ''}`,
            isUncertain ? vscode.DiagnosticSeverity.Information : severity
        );

        diag.source = 'LeakGuard';
        diag.code = leak.status || 'LEAK';

        const actions = [];
        if (!isUncertain) {
            actions.push({
                title: 'Add close()',
                command: 'leakguard.addClose',
                arguments: [document, line, leak.resource_name]
            });
        }
        diag.code = {
            value: leak.status || 'LEAK',
            target: vscode.Uri.parse('https://github.com/leakguard#leak-types')
        };

        diagnostics.push(diag);
    }

    DIAGNOSTICS_COLLECTION.set(document.uri, diagnostics);
}

function scanAllOpenFiles() {
    for (const doc of vscode.workspace.textDocuments) {
        if (doc.languageId === 'python') {
            scanDocument(doc);
        }
    }
}

function activate(context) {
    DIAGNOSTICS_COLLECTION.clear();

    vscode.workspace.onDidSaveTextDocument((doc) => {
        const config = vscode.workspace.getConfiguration('leakguard');
        if (config.get('scanOnSave', true)) {
            scanDocument(doc);
        }
    });

    vscode.workspace.onDidOpenTextDocument((doc) => {
        if (doc.languageId === 'python') {
            scanDocument(doc);
        }
    });

    vscode.workspace.onDidCloseTextDocument((doc) => {
        DIAGNOSTICS_COLLECTION.delete(doc.uri);
    });

    const scanFileCmd = vscode.commands.registerCommand('leakguard.scanFile', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'python') {
            scanDocument(editor.document);
            vscode.window.showInformationMessage('LeakGuard: File scanned.');
        } else {
            vscode.window.showWarningMessage('LeakGuard: No active Python file.');
        }
    });

    const scanWorkspaceCmd = vscode.commands.registerCommand('leakguard.scanWorkspace', async () => {
        await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, title: 'LeakGuard: Scanning workspace...' },
            async () => {
                const files = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**');
                for (const file of files) {
                    const doc = await vscode.workspace.openTextDocument(file);
                    await scanDocument(doc);
                }
                const count = DIAGNOSTICS_COLLECTION.size;
                vscode.window.showInformationMessage(`LeakGuard: Workspace scan complete. ${count} file(s) with findings.`);
            }
        );
    });

    const addCloseCmd = vscode.commands.registerCommand('leakguard.addClose', async (document, line, varName) => {
        const edit = new vscode.WorkspaceEdit();
        const insertLine = line + 1;
        const lineText = document.lineAt(line).text;
        const indent = lineText.match(/^(\s*)/)[1];
        const closeLine = `${indent}${varName}.close()  # [LeakGuard]\n`;
        edit.insert(document.uri, new vscode.Position(insertLine, 0), closeLine);
        await vscode.workspace.applyEdit(edit);
    });

    context.subscriptions.push(DIAGNOSTICS_COLLECTION, scanFileCmd, scanWorkspaceCmd, addCloseCmd);

    scanAllOpenFiles();
}

function deactivate() {
    DIAGNOSTICS_COLLECTION.clear();
}

module.exports = { activate, deactivate };
