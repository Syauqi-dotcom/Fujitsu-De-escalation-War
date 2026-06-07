import json
import os
import argparse
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "changelog.json")
MD_FILE = os.path.join(os.path.dirname(__file__), "LOG_VISUAL.md")

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, 'r') as f:
        return json.load(f)

def save_logs(logs):
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=4)
    generate_markdown(logs)

def add_log(file, item_type, name, reason):
    """
    python3 logs/logger.py add --file "src/nama_file.py" --type "function" --name "nama_fungsi" --reason "Alasan..."
    python3 logs/logger.py build
    """
    logs = load_logs()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file": file,
        "type": item_type,
        "name": name,
        "reason": reason
    }
    logs.append(entry)
    save_logs(logs)
    print(f"✅ Log berhasil ditambahkan: {name} ({item_type}) di {file}")

def generate_markdown(logs):
    md_content = "# Visualisasi Log Perubahan Kode\n\n"
    md_content += "File ini dibuat secara otomatis oleh `logger.py`. File ini memvisualisasikan data dari `changelog.json`.\n\n"
    md_content += "| Waktu | File | Tipe | Nama | Alasan/Tujuan |\n"
    md_content += "|---|---|---|---|---|\n"
    
    # Menampilkan dari yang terbaru ke terlama
    for log in reversed(logs):
        md_content += f"| {log['timestamp']} | `{log['file']}` | **{log['type'].capitalize()}** | `{log['name']}` | {log['reason']} |\n"
    
    with open(MD_FILE, 'w') as f:
        f.write(md_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Otomatisasi Log Perubahan Kode")
    subparsers = parser.add_subparsers(dest="command")

    # Perintah 'add'
    parser_add = subparsers.add_parser("add", help="Tambah log fungsi/variabel baru")
    parser_add.add_argument("--file", required=True, help="Path ke file yang diubah (contoh: src/main.py)")
    parser_add.add_argument("--type", required=True, choices=['function', 'variable', 'class', 'module'], help="Tipe elemen yang ditambahkan")
    parser_add.add_argument("--name", required=True, help="Nama fungsi/variabel/class")
    parser_add.add_argument("--reason", required=True, help="Alasan/Tujuan penambahan elemen ini")

    # Perintah 'build'
    parser_view = subparsers.add_parser("build", help="Buat/update file visual markdown (LOG_VISUAL.md)")

    args = parser.parse_args()

    if args.command == "add":
        add_log(args.file, args.type, args.name, args.reason)
    elif args.command == "build":
        logs = load_logs()
        generate_markdown(logs)
        print(f"✅ Visualisasi {MD_FILE} berhasil di-generate ulang!")
    else:
        parser.print_help()
