import urllib.request, json

data = json.loads(urllib.request.urlopen("http://localhost:8000/api/recommendations?limit=5").read())
print("Recommendations returned:", len(data))
for r in data[:3]:
    print("  #%s | %s | slot=%s | score=%s" % (r["content_id"], r["platform"], r["recommended_slot"], r["score"]))

stats = json.loads(urllib.request.urlopen("http://localhost:8000/api/stats").read())
print("Stats: total_posts=%s, avg_score=%s" % (stats["total_posts"], stats["avg_score"]))

hm = json.loads(urllib.request.urlopen("http://localhost:8000/api/heatmap").read())
print("Heatmap platforms:", list(hm.keys()))
