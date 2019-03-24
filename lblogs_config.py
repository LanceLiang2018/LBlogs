import yaml


def config(src,
           name='My Blog',
           email='example@example.com',
           author='Admin',
           url='http://lblogs.lanceliang2018.xyz/',
           resume_site='http://www.hifreud.com/Resume.io/',
           github='https://github.com/LanceLiang2018/',
           baseurl='',
           description='Actually, less is more!',
           meta_description='个人博客',
           motto='It\'s our wits that make us men.',
           banner='学而不思则罔，思而不学则殆。',
           baidu_analysis='694242349c87261f70ca00c61c19fca7'):
    yml = yaml.load(src)
    yml['name'] = name
    yml['author'] = author
    yml['email'] = email
    yml['url'] = url
    yml['baseurl'] = baseurl
    yml['baidu_analysis'] = baidu_analysis
    yml['banner'] = banner
    yml['motto'] = motto
    yml['meta_description'] = meta_description
    yml['description'] = description
    yml['github'] = github
    yml['resume_site'] = resume_site

    res = yaml.dump(yml)
    return res


if __name__ == '__main__':
    config('')
