# Dengue Early-Warning System — Clayton Kwok

## One-liner: End-to-end dengue early-warning pipeline (data → features → model → API → demo) with a prebuilt Docker image for easy testing.

---

# Quick demo

Run directly with the published Docker image:

## pull image
docker pull ghcr.io/syterz/west-malaysia-dengue-forecasting-model:latest  

## run container
docker run -p 5000:5000 ghcr.io/syterz/west-malaysia-dengue-forecasting-model:latest  

## test (example request)
curl "http://localhost:5000/forecast?district=A&horizon=1"

## test in local host
Run http://127.0.0.1:5000/healthz to check status (is it working or not)
http://127.0.0.1:5000/forecast to check future forecast
http://127.0.0.1:5000/plot to check for the plot

# License

This project’s **source code** and **Docker image** are released under the [MIT License](LICENSE).  
You are free to use, modify, and distribute them, provided attribution is given. 

- **Source code**: Licensed under the [MIT License](LICENSE).  
- **Docker image**: The prebuilt Docker image published under [GitHub Packages](https://github.com/users/Syterz/packages/container/package/west-malaysia-dengue-forecasting-model) is provided under the same MIT License.

## Data License
The demonstration dataset used in this repository was derived from OPEN DENGUE Project, and Malaysia Open Data Portal uploaded by Dr. Zuhaida Binti A. Jalil, and NASA Prediction Of Worldwide Energy Resources which are licensed under **Creative Commons Attribution 3.0 (CC BY 3.0)**.

Accordingly, any reuse of the dataset must comply with the terms of the CC BY 3.0 license.  
See: https://creativecommons.org/licenses/by/3.0/.

One of the dataset also came from the Portal Rasmi KEMENTERIAN KESIHATAN MALAYSIA which was under Data Terbuka Kerajaan 1.0.

Additionally, the recent dataset of dengue cases are obtained from iDengue which I was told that it should be fine to be used

