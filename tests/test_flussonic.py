from app.clients.flussonic import FlussonicClient
from app.clients.stream_provider import ProviderActiveSourceCounters


def test_active_source_counters_include_both_lb_wisp_hosts() -> None:
    client = FlussonicClient.__new__(FlussonicClient)
    items = [
        {"inputs": [{"url": url, "stats": {"active": True}}]}
        for url in (
            "http://lb.wisp.cat/channel/index.m3u8",
            "https://CDN.SHINDA.TV:443/channel/index.m3u8",
            "http://online24.example/channel/index.m3u8",
            "http://restream.pw/channel/index.m3u8",
            "http://185.96.80.44/channel/index.m3u8",
        )
    ]
    items.extend([
        {
            "inputs": [
                {
                    "url": "http://lb.wisp.cat/channel/index.m3u8",
                    "stats": {"active": False},
                },
                {
                    "url": "http://cdn.shinda.tv/channel/index.m3u8",
                    "stats": {"active": False},
                },
                {
                    "url": "http://other.example/channel/index.m3u8",
                    "stats": {"active": True},
                },
            ],
        },
        {"inputs": [{"url": "http://lb.wisp.cat/channel/index.m3u8"}]},
    ])

    assert client._count_active_source_counters(items) == ProviderActiveSourceCounters(
        online24=2,
        restream=2,
        other=2,
    )
